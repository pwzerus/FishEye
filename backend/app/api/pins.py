"""/api/pins — community catch pins, and /api/media — their photos."""
from __future__ import annotations

from datetime import date
from typing import NoReturn

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth_deps import optional_user, require_user, same_origin
from app.api.deps import get_db
from app.api.params import DbId
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
from app.models.waterbody import Waterbody
from app.schemas.pins import (
    PinAuthorOut,
    PinDetailOut,
    PinLakeOut,
    PinOptionsOut,
    PinPhotoOut,
    PinSummaryOut,
    PinUpdateIn,
    ReportIn,
    ReportOut,
)
from app.services import audit
from app.services import pins as svc
from app.services.media import get_store
from app.services.pins import PinError

router = APIRouter(tags=["pins"], dependencies=[Depends(same_origin)])

UNDER_MODERATION = "This pin is under moderation, so it can't be changed or deleted until a moderator reviews it."

create_by_user = RateLimiter(limit=30, window_seconds=60 * 60)
report_by_user = RateLimiter(limit=20, window_seconds=60 * 60)


def _raise(exc: PinError) -> NoReturn:
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


def summary_fields(pin: CatchPin, user: User | None, lakes: dict[int, Waterbody]) -> dict:
    lake = lakes.get(pin.waterbody_id) if pin.waterbody_id else None
    first = pin.photos[0] if pin.photos else None
    return {
        "id": pin.id,
        "latitude": pin.latitude,
        "longitude": pin.longitude,
        "title": pin.title,
        "species_slug": pin.species_slug,
        "species_label": svc.species_label(pin),
        "caught_on": pin.caught_on,
        "created_at": pin.created_at,
        "visibility": pin.visibility,
        "status": pin.status,
        "status_reason": pin.status_reason,
        "author": PinAuthorOut(id=pin.user.id, display_name=pin.user.display_name),
        "lake": PinLakeOut(id=lake.id, name=lake.name) if lake else None,
        "photo_count": len(pin.photos),
        "thumb_url": _media_url(first, thumb=True) if first else None,
        "is_mine": user is not None and user.id == pin.user_id,
    }


def lakes_for(db: Session, pins: list[CatchPin]) -> dict[int, Waterbody]:
    ids = {p.waterbody_id for p in pins if p.waterbody_id}
    if not ids:
        return {}
    return {w.id: w for w in db.scalars(select(Waterbody).where(Waterbody.id.in_(ids)))}


def detail_out(db: Session, pin: CatchPin, user: User | None) -> PinDetailOut:
    reported = user is not None and db.scalar(
        select(PinReport.id).where(PinReport.pin_id == pin.id, PinReport.reporter_id == user.id)
    ) is not None
    return PinDetailOut(
        **summary_fields(pin, user, lakes_for(db, [pin])),
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
    return west, south, east, north


def _read_uploads(files: list[UploadFile] | None, room: int) -> list[bytes]:
    """Reads uploads only after checking how many there are, one at a time,
    each capped: never more than `room` photos of max_photo_bytes in memory."""
    parts = [f for f in files or [] if f.filename]
    if len(parts) > room:
        raise HTTPException(status_code=422, detail=f"A pin can have up to {get_settings().max_photos_per_pin} photos.")
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


@router.get("/pins", response_model=list[PinSummaryOut])
def list_pins(
    bbox: str | None = None,
    species: str | None = None,
    mine: bool = False,
    limit: int = Query(default=200, ge=1, le=svc.MAX_LIST),
    user: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
) -> list[PinSummaryOut]:
    pins = svc.list_pins(db, user, bbox=_parse_bbox(bbox), species=species, mine=mine, limit=limit)
    lakes = lakes_for(db, pins)
    return [PinSummaryOut(**summary_fields(p, user, lakes)) for p in pins]


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
    latitude: float = Form(...),
    longitude: float = Form(...),
    title: str = Form(..., max_length=200),
    note: str | None = Form(default=None, max_length=2000),
    species_slug: str | None = Form(default=None),
    species_other: str | None = Form(default=None, max_length=120),
    caught_on: date | None = Form(default=None),
    visibility: str = Form(default=VISIBILITY_PUBLIC),
    photos: list[UploadFile] | None = File(default=None),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> PinDetailOut:
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
        )
        pin = svc.create_pin(db, user, fields, uploads, get_store())
    except PinError as exc:
        db.rollback()
        _raise(exc)
    db.commit()
    db.refresh(pin)
    return detail_out(db, pin, user)


def _owned_pin(db: Session, pin_id: int, user: User) -> CatchPin:
    pin = db.get(CatchPin, pin_id)
    if pin is None or not svc.can_view(pin, user):
        raise HTTPException(status_code=404, detail="No such pin.")
    if pin.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the person who pinned this can change it.")
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
        )
    except PinError as exc:
        _raise(exc)
    pin.title, pin.note = fields.title, fields.note
    pin.species_slug, pin.species_other = fields.species_slug, fields.species_other
    pin.caught_on, pin.visibility = fields.caught_on, fields.visibility
    db.commit()
    db.refresh(pin)
    return detail_out(db, pin, user)


@router.delete("/pins/{pin_id}", status_code=204, response_class=Response)
def delete_pin(pin_id: DbId, user: User = Depends(require_user), db: Session = Depends(get_db)) -> Response:
    pin = db.get(CatchPin, pin_id)
    if pin is None or not svc.can_view(pin, user) or pin.user_id != user.id:
        raise HTTPException(status_code=404, detail="No such pin.")
    if pin.status != PIN_PUBLISHED:
        # A hidden or removed pin is a moderation case; deleting it would
        # also delete the reports against it. It's already invisible to
        # everyone else, so nothing is lost by waiting for the review.
        raise HTTPException(status_code=409, detail=UNDER_MODERATION)
    open_reports = svc.open_report_count(db, pin.id)
    if open_reports:
        audit.record(db, user, "pin.deleted_by_owner", "pin", pin.id, title=pin.title, open_reports=open_reports)
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
        raise HTTPException(status_code=409, detail="You've already reported this pin.") from None
    db.commit()
    return ReportOut(received=True, pin_hidden=hidden)


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
