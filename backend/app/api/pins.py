"""/api/pins — community catch pins, and /api/media — their photos."""
from __future__ import annotations

import math
from datetime import date
from typing import NoReturn

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api import rate_limits
from app.api.auth_deps import optional_user, require_user, same_origin
from app.api.deps import get_db
from app.api.rate_limits import client_ip
from app.api.params import MAX_ID, DbId
from app.core.config import get_settings
from app.core.security import RateLimiter
from app.models.community import (
    PIN_PUBLISHED,
    VISIBILITY_PUBLIC,
    CatchPin,
    PinPhoto,
    PinReport,
    User,
)
from app.models.water import River
from app.models.waterbody import Waterbody
from app.schemas.pins import (
    FishCandidateOut,
    FishIdOut,
    FishVerdictOut,
    PinAuthorOut,
    PinDetailOut,
    PinLakeOut,
    PinOptionsOut,
    PinPhotoOut,
    PinSummaryOut,
    PinUpdateIn,
    PinWaterOut,
    PlaceOut,
    PlacesOut,
    ReportIn,
    ReportOut,
    WaterGroupOut,
    WhereOut,
    WhereWaterOut,
)
from app.knowledge.jurisdictions import STATE_NAMES
from app.services import alerts, audit, counties, email_verification, fish_id, social, water
from app.services import pins as svc
from app.services.email_verification import VerificationError
from app.services.fish_id_classes import BY_SLUG, CLAIM_GROUPS, GUIDE, SAME_FISH, group_label
from app.services.media import PhotoRejected, clean_photo, get_store
from app.services.pins import PinError

router = APIRouter(tags=["pins"], dependencies=[Depends(same_origin)])

UNDER_MODERATION = "This catch is under moderation, so it can't be changed until a moderator reviews it. You can still delete it."

create_by_user = RateLimiter(limit=30, window_seconds=60 * 60)
report_by_user = RateLimiter(limit=20, window_seconds=60 * 60)
# Each check is a few hundred milliseconds of the server's CPU.
fish_id_by_user = RateLimiter(limit=60, window_seconds=60 * 60)
# Signed out, a photo check is a trial: a few a day from one address, and a
# daily total across every signed-out visitor, so a script can't keep the
# server's CPU busy. The model runs on this server; no paid API is called.
fish_id_trial_by_ip = RateLimiter(limit=5, window_seconds=24 * 60 * 60)
fish_id_trial_everyone = RateLimiter(limit=500, window_seconds=24 * 60 * 60)
TRIAL_USED = "You've used today's free photo checks. Sign in (it's free) to check more."
TRIAL_FULL = "Free photo checks are at today's limit. Sign in (it's free) to keep checking."


def _raise(exc: PinError) -> NoReturn:
    raise HTTPException(status_code=exc.status, detail=exc.message) from exc


def _verified(user: User) -> None:
    """Sharing and reporting wait for a confirmed email address when
    EMAIL_VERIFICATION is on (services/email_verification.py)."""
    try:
        email_verification.require_verified(user)
    except VerificationError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc


def _throttle(limiter: RateLimiter, user: User) -> None:
    key = str(user.id)
    wait = limiter.blocked_for(key)
    if wait > 0:
        raise HTTPException(
            status_code=429,
            detail="You're doing that a lot. Try again later.",
            headers={"Retry-After": str(int(wait) + 1)},
        )
    limiter.hit(key)


def _media_url(photo: PinPhoto, thumb: bool = False) -> str:
    base = get_settings().api_public_url.rstrip("/")
    return f"{base}/api/media/photos/{photo.id}" + ("?size=thumb" if thumb else "")


def _group_label(pin: CatchPin) -> str | None:
    """What a "group" check confirmed: "a black bass" for a pin that says
    smallmouth when the photo can't tell which black bass it is."""
    claimed = BY_SLUG.get(pin.species_slug or "")
    return group_label(CLAIM_GROUPS.get(pin.species_slug or "") or (claimed.group if claimed else None))


Waters = tuple[dict[int, Waterbody], dict[int, River]]


def _water_out(pin: CatchPin, waters: Waters) -> PinWaterOut | None:
    lakes, rivers = waters
    if pin.waterbody_id in lakes:
        return PinWaterOut(kind=water.LAKE, id=pin.waterbody_id, name=lakes[pin.waterbody_id].name)
    if pin.river_id in rivers:
        return PinWaterOut(kind=water.RIVER, id=pin.river_id, name=rivers[pin.river_id].name)
    return None


def summary_fields(pin: CatchPin, user: User | None, waters: Waters, likes: social.Social | None = None) -> dict:
    lake = waters[0].get(pin.waterbody_id) if pin.waterbody_id else None
    likes = likes or social.Social()
    first = pin.photos[0] if pin.photos else None
    # Others see the public point unless the angler shared the spot (ADR 0038).
    latitude, longitude, shown = svc.shown_point(pin, user)
    return {
        "id": pin.id,
        "latitude": latitude,
        "longitude": longitude,
        "location_shown": shown,
        "share_exact": pin.share_exact,
        "public_place": svc.PLACE_EXACT if pin.share_exact else (pin.public_place or svc.PLACE_AREA),
        "title": pin.title,
        "species_slug": pin.species_slug,
        "species_label": svc.species_label(pin),
        "species_check": pin.species_check,
        "species_check_label": _group_label(pin) if pin.species_check == fish_id.GROUP else None,
        "caught_on": pin.caught_on,
        "created_at": pin.created_at,
        "visibility": pin.visibility,
        "status": pin.status,
        "status_reason": pin.status_reason,
        "author": PinAuthorOut(id=pin.user.id, display_name=pin.user.display_name),
        "lake": PinLakeOut(id=lake.id, name=lake.name) if lake else None,
        "water": _water_out(pin, waters),
        "photo_at_spot": bool(pin.photo_at_spot),
        "state_code": pin.state_code,
        "county_geoid": pin.county_geoid,
        "county_name": pin.county_name,
        "photo_count": len(pin.photos),
        "thumb_url": _media_url(first, thumb=True) if first else None,
        "is_mine": user is not None and user.id == pin.user_id,
        "like_count": likes.likes,
        "comment_count": likes.comments,
        "liked_by_me": likes.liked,
    }


def waters_for(db: Session, pins: list[CatchPin]) -> Waters:
    lake_ids = {p.waterbody_id for p in pins if p.waterbody_id}
    river_ids = {p.river_id for p in pins if p.river_id}
    lakes = {w.id: w for w in db.scalars(select(Waterbody).where(Waterbody.id.in_(lake_ids)))} if lake_ids else {}
    rivers = {r.id: r for r in db.scalars(select(River).where(River.id.in_(river_ids)))} if river_ids else {}
    return lakes, rivers


def detail_out(db: Session, pin: CatchPin, user: User | None) -> PinDetailOut:
    reported = user is not None and db.scalar(
        select(PinReport.id).where(PinReport.pin_id == pin.id, PinReport.reporter_id == user.id)
    ) is not None
    return PinDetailOut(
        **summary_fields(pin, user, waters_for(db, [pin]), social.counts(db, [pin.id], user)[pin.id]),
        note=pin.note,
        photos=[
            PinPhotoOut(id=p.id, url=_media_url(p), thumb_url=_media_url(p, thumb=True), width=p.width, height=p.height)
            for p in pin.photos
        ],
        can_edit=svc.can_edit(pin, user),
        can_report=(
            user is not None
            and user.id != pin.user_id
            and pin.visibility == VISIBILITY_PUBLIC
            and pin.status == PIN_PUBLISHED
            and not reported
        ),
        reported_by_me=reported,
    )


def _parse_bbox(bbox: str | None) -> tuple[float, float, float, float] | None:
    if not bbox:
        return None
    try:
        west, south, east, north = (float(v) for v in bbox.split(","))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="bbox is west,south,east,north") from exc
    if not all(math.isfinite(v) for v in (west, south, east, north)):
        raise HTTPException(status_code=422, detail="bbox is west,south,east,north")
    return west, south, east, north


def _read_uploads(files: list[UploadFile] | None, room: int) -> list[bytes]:
    """Reads uploads only after checking how many there are, one at a time,
    each capped: never more than `room` photos of max_photo_bytes in memory."""
    parts = [f for f in files or [] if f.filename]
    if len(parts) > room:
        raise HTTPException(status_code=422, detail=f"A catch can have up to {get_settings().max_photos_per_pin} photos.")
    out: list[bytes] = []
    cap = get_settings().max_photo_bytes
    for f in parts:
        # One byte past the cap is enough to know it's too big.
        data = f.file.read(cap + 1)
        if len(data) > cap:
            raise HTTPException(status_code=413, detail=f"Photos can be up to {cap // (1024 * 1024)} MB.")
        out.append(data)
    return out


# ----------------------------------------------------------------- reads


@router.get("/pins/options", response_model=PinOptionsOut)
def pin_options() -> PinOptionsOut:
    s = get_settings()
    return PinOptionsOut(
        species=[{"slug": slug, "label": label} for slug, label in sorted(svc.SPECIES_LABELS.items(), key=lambda kv: kv[1])],
        report_reasons=[{"id": k, "label": v} for k, v in svc.REPORT_REASONS.items()],
        max_photos=s.max_photos_per_pin,
        max_photo_mb=s.max_photo_bytes // (1024 * 1024),
    )


StateParam = Query(default=None, pattern=r"^[A-Za-z]{2}$")
CountyParam = Query(default=None, pattern=r"^\d{5}$")


@router.get("/pins/places", response_model=PlacesOut)
def pin_places(
    state: str | None = StateParam,
    county: str | None = CountyParam,
    species: str | None = None,
    mine: bool = False,
    user: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
) -> PlacesOut:
    """Browsing catches: the states with catches; with `state`, its
    counties; with `county`, its lakes. Each with how many catches."""
    level = "lake" if county else "county" if state else "state"
    found = svc.places(db, user, state=state, county=county, species=species, mine=mine)
    c = counties.index().by_geoid.get(county) if county and counties.index() else None
    state = state or (c.state if c else None)
    return PlacesOut(
        level=level,
        places=[PlaceOut(id=p.id, name=p.name, count=p.count) for p in found],
        state_name=STATE_NAMES.get(state.upper(), state.upper()) if state else None,
        county_name=c.name if c else None,
    )


@router.get("/pins/where", response_model=WhereOut)
def pin_where(
    lat: float = Query(ge=-90, le=90),
    lng: float = Query(ge=-180, le=180),
    db: Session = Depends(get_db),
) -> WhereOut:
    """The county a point is in: where "near me" opens the catches; and the
    water a catch there would be on (ADR 0040), for the map while placing
    one. Not stored or logged."""
    c = counties.county_at(lat, lng)
    match = water.find_water(db, lat, lng)
    return WhereOut(
        state_code=c.state if c else None,
        state_name=STATE_NAMES.get(c.state, c.state) if c else None,
        county_geoid=c.geoid if c else None,
        county_name=c.name if c else None,
        water=WhereWaterOut(kind=match.kind, id=match.id, name=match.name, distance_m=match.distance_m)
        if match
        else None,
        # Outside the US nothing but mapped water will do, whatever the data.
        water_required=c is None or water.data_ready(db, c.state),
    )


@router.get("/pins/waters", response_model=list[WaterGroupOut])
def pin_waters(
    bbox: str,
    species: str | None = None,
    user: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
) -> list[WaterGroupOut]:
    """Other people's catches in view, counted per lake and per river in
    each county (ADR 0040). The viewer's own catches come from /pins."""
    box = _parse_bbox(bbox)
    if box is None:
        raise HTTPException(status_code=422, detail="bbox is west,south,east,north")
    out: list[WaterGroupOut] = []
    for g in svc.water_groups(db, user, bbox=box, species=species):
        counted: dict[str, int] = {}
        for p in g.pins:
            if (label := svc.species_label(p)) is not None:
                counted[label] = counted.get(label, 0) + 1
        with_photo = next((p for p in g.pins if p.photos), None)
        out.append(WaterGroupOut(
            kind=g.kind, id=g.id, state_code=g.state_code, county_geoid=g.county_geoid, name=g.name,
            county_name=g.county_name,
            latitude=g.latitude, longitude=g.longitude, count=len(g.pins),
            latest_at=g.pins[0].created_at,
            species=[label for label, _ in sorted(counted.items(), key=lambda kv: -kv[1])[:3]],
            thumb_url=_media_url(with_photo.photos[0], thumb=True) if with_photo else None,
        ))
    return out


@router.get("/pins", response_model=list[PinSummaryOut])
def list_pins(
    bbox: str | None = None,
    species: str | None = None,
    mine: bool = False,
    state: str | None = StateParam,
    county: str | None = CountyParam,
    lake: int | None = Query(default=None, ge=0, le=MAX_ID),
    river: int | None = Query(default=None, ge=1, le=MAX_ID),
    author: int | None = Query(default=None, ge=1, le=MAX_ID),
    limit: int = Query(default=200, ge=1, le=svc.MAX_LIST),
    user: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
) -> list[PinSummaryOut]:
    pins = svc.list_pins(
        db, user, bbox=_parse_bbox(bbox), species=species, mine=mine,
        state=state, county=county, lake=lake, river=river, author=author, limit=limit,
    )
    waters = waters_for(db, pins)
    likes = social.counts(db, [p.id for p in pins], user)
    return [PinSummaryOut(**summary_fields(p, user, waters, likes[p.id])) for p in pins]


@router.get("/pins/{pin_id}", response_model=PinDetailOut)
def get_pin(pin_id: DbId, user: User | None = Depends(optional_user), db: Session = Depends(get_db)) -> PinDetailOut:
    try:
        pin = svc.get_visible_pin(db, pin_id, user)
    except PinError as exc:
        _raise(exc)
    return detail_out(db, pin, user)


# ---------------------------------------------------------------- writes


# Plain `def`, not `async def`: decoding and re-encoding photos is CPU work,
# and FastAPI runs sync routes in a threadpool instead of blocking the event
# loop for every other request.
@router.post("/pins", response_model=PinDetailOut, status_code=201)
def create_pin(
    background: BackgroundTasks,
    latitude: float = Form(...),
    longitude: float = Form(...),
    title: str = Form(..., max_length=200),
    note: str | None = Form(default=None, max_length=2000),
    species_slug: str | None = Form(default=None),
    species_other: str | None = Form(default=None, max_length=120),
    caught_on: date | None = Form(default=None),
    visibility: str = Form(default=VISIBILITY_PUBLIC),
    share_exact: bool = Form(default=False),
    photos: list[UploadFile] | None = File(default=None),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> PinDetailOut:
    _verified(user)
    _throttle(create_by_user, user)
    uploads = _read_uploads(photos, get_settings().max_photos_per_pin)
    try:
        fields = svc.validate(
            latitude=latitude,
            longitude=longitude,
            title=title,
            note=note,
            species_slug=species_slug,
            species_other=species_other,
            caught_on=caught_on,
            visibility=visibility,
            share_exact=share_exact,
        )
        pin = svc.create_pin(db, user, fields, uploads, get_store())
    except PinError as exc:
        db.rollback()
        _raise(exc)
    notices = alerts.notices_for(db, pin)
    db.commit()
    db.refresh(pin)
    # After the response: a slow mail server shouldn't hold up the post.
    if notices:
        background.add_task(alerts.send, notices)
    return detail_out(db, pin, user)


def _owned_pin(db: Session, pin_id: int, user: User) -> CatchPin:
    pin = db.get(CatchPin, pin_id)
    if pin is None or not svc.can_view(pin, user):
        raise HTTPException(status_code=404, detail="No such catch.")
    if pin.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the person who shared this catch can change it.")
    if not svc.can_edit(pin, user):
        raise HTTPException(status_code=409, detail=UNDER_MODERATION)
    return pin


@router.patch("/pins/{pin_id}", response_model=PinDetailOut)
def update_pin(
    payload: PinUpdateIn,
    pin_id: DbId,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> PinDetailOut:
    pin = _owned_pin(db, pin_id, user)
    if (payload.latitude is None) != (payload.longitude is None):
        raise HTTPException(status_code=422, detail="Send both latitude and longitude, or neither.")
    # Species is one choice: a guide species, free text, or nothing. Setting
    # either kind replaces the other.
    slug, other = pin.species_slug, pin.species_other
    if payload.clear_species:
        slug, other = None, None
    elif payload.species_slug is not None:
        slug, other = payload.species_slug, None
    elif payload.species_other is not None:
        slug, other = None, payload.species_other
    try:
        fields = svc.validate(
            latitude=pin.latitude,
            longitude=pin.longitude,
            title=payload.title if payload.title is not None else pin.title,
            note=None if payload.clear_note else (payload.note if payload.note is not None else pin.note),
            species_slug=slug,
            species_other=other,
            caught_on=None
            if payload.clear_caught_on
            else (payload.caught_on if payload.caught_on is not None else pin.caught_on),
            visibility=payload.visibility or pin.visibility,
            share_exact=pin.share_exact if payload.share_exact is None else payload.share_exact,
        )
    except PinError as exc:
        _raise(exc)
    if (fields.species_slug, fields.species_other) != (pin.species_slug, pin.species_other):
        # A different fish is checked against the catch's photo, like a new pin.
        try:
            svc.recheck_species(db, pin, fields.species_slug, fields.species_other, get_store())
        except PinError as exc:
            db.rollback()
            _raise(exc)
    pin.title, pin.note = fields.title, fields.note
    pin.species_slug, pin.species_other = fields.species_slug, fields.species_other
    pin.caught_on, pin.visibility = fields.caught_on, fields.visibility
    if payload.latitude is not None and payload.longitude is not None:
        try:
            svc.move_pin(db, pin, payload.latitude, payload.longitude)
        except PinError as exc:
            db.rollback()
            _raise(exc)
    if fields.share_exact != pin.share_exact:
        pin.share_exact = fields.share_exact
        svc.set_public_point(db, pin)
    db.commit()
    db.refresh(pin)
    return detail_out(db, pin, user)


@router.delete("/pins/{pin_id}", status_code=204, response_class=Response)
def delete_pin(pin_id: DbId, user: User = Depends(require_user), db: Session = Depends(get_db)) -> Response:
    pin = db.get(CatchPin, pin_id)
    if pin is None or not svc.can_view(pin, user) or pin.user_id != user.id:
        raise HTTPException(status_code=404, detail="No such catch.")
    # An owner can always take their own catch down, even while it is
    # hidden or removed (it can't be edited then: see svc.can_edit). The
    # reports go with it, so deleting one that was moderated or reported
    # is recorded for the admins.
    open_reports = svc.open_report_count(db, pin.id)
    if open_reports or pin.status != PIN_PUBLISHED:
        audit.record(
            db, user, "pin.deleted_by_owner", "pin", pin.id,
            title=pin.title, status_before=pin.status, open_reports=open_reports,
        )
    svc.delete_pin(db, pin, get_store())
    db.commit()
    return Response(status_code=204)


@router.post("/pins/{pin_id}/photos", response_model=PinDetailOut)
def add_photos(
    pin_id: DbId,
    photos: list[UploadFile] = File(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> PinDetailOut:
    pin = _owned_pin(db, pin_id, user)
    uploads = _read_uploads(photos, get_settings().max_photos_per_pin - len(pin.photos))
    try:
        svc.add_photos(db, pin, uploads, get_store())
    except PinError as exc:
        db.rollback()
        _raise(exc)
    db.commit()
    db.refresh(pin)
    return detail_out(db, pin, user)


@router.delete("/pins/{pin_id}/photos/{photo_id}", response_model=PinDetailOut)
def delete_photo(
    pin_id: DbId, photo_id: DbId, user: User = Depends(require_user), db: Session = Depends(get_db)
) -> PinDetailOut:
    pin = _owned_pin(db, pin_id, user)
    try:
        svc.delete_photo(db, pin, photo_id, get_store())
    except PinError as exc:
        _raise(exc)
    db.commit()
    db.refresh(pin)
    return detail_out(db, pin, user)


@router.post("/pins/{pin_id}/reports", response_model=ReportOut, status_code=201)
def report_pin(
    payload: ReportIn, pin_id: DbId, user: User = Depends(require_user), db: Session = Depends(get_db)
) -> ReportOut:
    try:
        pin = svc.get_visible_pin(db, pin_id, user)
    except PinError as exc:
        _raise(exc)
    _verified(user)
    _throttle(report_by_user, user)
    try:
        hidden = svc.report_pin(db, pin, user, payload.reason, payload.detail)
    except PinError as exc:
        db.rollback()
        _raise(exc)
    except IntegrityError:
        # Two identical reports raced past the duplicate check; the unique
        # constraint caught the second.
        db.rollback()
        raise HTTPException(status_code=409, detail="You've already reported this catch.") from None
    db.commit()
    return ReportOut(received=True, pin_hidden=hidden)


# ------------------------------------------------------------ photo check


def _top_group(ident: fish_id.Identification) -> str | None:
    """The likeliest fish's kind, when it has look-alikes to share it with."""
    top = ident.fish(1)
    c = BY_SLUG.get(top[0].slug) if top else None
    if c is None or c.group is None or sum(1 for o in BY_SLUG.values() if o.group == c.group) < 2:
        return None
    return c.group


def _trial(request: Request) -> None:
    """A signed-out photo check: refused before any work once the address or
    everyone signed out has used the day's allowance."""
    if not get_settings().rate_limits_enabled:
        return
    ip = client_ip(request)
    own = fish_id_trial_by_ip.blocked_for(ip)
    shared = fish_id_trial_everyone.blocked_for(rate_limits.EVERYONE)
    if own > 0 or shared > 0:
        raise HTTPException(
            status_code=429,
            detail=TRIAL_USED if own > 0 else TRIAL_FULL,
            headers={"Retry-After": str(int(max(own, shared)) + 1)},
        )
    fish_id_trial_by_ip.hit(ip)
    fish_id_trial_everyone.hit(rate_limits.EVERYONE)


@router.post("/fish-id", response_model=FishIdOut)
def identify_fish(
    request: Request,
    photo: UploadFile = File(...),
    species_slug: str | None = Form(default=None),
    species_other: str | None = Form(default=None, max_length=120),
    user: User | None = Depends(optional_user),
) -> FishIdOut:
    """What fish a photo shows, and, given one, whether it backs the claim:
    the catch form asks as soon as a photo is chosen, so a mismatch is said
    before anything is saved. Saving checks again (services/pins.py); this
    answer is advice to the form, never trusted.

    Signed out, it is a trial with a small daily allowance (_trial)."""
    if user is None:
        _trial(request)
    else:
        _throttle(fish_id_by_user, user)
    data = _read_uploads([photo], 1)[0]
    try:
        cleaned = clean_photo(data)
    except PhotoRejected as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        recognizer = fish_id.get_recognizer()
    except fish_id.FishIdUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if recognizer is None:
        return FishIdOut(available=False, model=None, fish_probability=None, candidates=[], verdict=None)
    try:
        claim = svc.claimed_species(species_slug, species_other)
    except PinError as exc:
        _raise(exc)
    ident = recognizer.identify(cleaned.full)
    verdict = fish_id.check_claim(ident, claim) if (species_slug or species_other) else None
    # No guesses about a photo that shows no fish: the form used to offer them.
    shows_fish = ident.fish_probability >= fish_id.POLICY.min_fish
    return FishIdOut(
        available=True,
        model=recognizer.name,
        fish_probability=round(ident.fish_probability, 3),
        candidates=[
            FishCandidateOut(
                slug=c.slug,
                label=c.label,
                probability=round(c.probability, 3),
                in_guides=c.kind == GUIDE,
                guide_slug=c.slug if c.kind == GUIDE else SAME_FISH.get(c.slug),
            )
            for c in (ident.fish(3) if shows_fish else ())
        ],
        group=_top_group(ident) if shows_fish else None,
        group_probability=round(ident.group_probability(_top_group(ident)), 3) if shows_fish and _top_group(ident) else None,
        verdict=FishVerdictOut(
            status=verdict.status,
            accepted=verdict.accepted,
            detected=verdict.detected,
            detected_label=BY_SLUG[verdict.detected].common if verdict.detected in BY_SLUG else None,
            detected_in_guides=verdict.detected in svc.SPECIES_LABELS,
            message=verdict.message,
        )
        if verdict
        else None,
    )


# ----------------------------------------------------------------- media


@router.get("/media/photos/{photo_id}")
def photo_file(
    photo_id: DbId,
    size: str = "full",
    user: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    photo = db.get(PinPhoto, photo_id)
    if photo is None or not svc.can_view(photo.pin, user):
        raise HTTPException(status_code=404, detail="No such photo.")
    path = get_store().path(photo.storage_key, "thumb" if size == "thumb" else "full")
    if path is None:
        raise HTTPException(status_code=404, detail="No such photo.")
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={
            # Browser cache only, never a shared one: a CDN holding a copy
            # would keep serving a photo after its pin went private or was
            # hidden by a moderator.
            "Cache-Control": "private, max-age=600",
            "X-Content-Type-Options": "nosniff",
        },
    )
