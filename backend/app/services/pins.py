"""Community catch pins: who may see and change what, and moderation.

Visibility, in one place (`can_view`), so the list endpoint, the detail
endpoint and the media endpoint can't drift apart:
- the owner always sees their own pins, whatever their state;
- admins see everything;
- everyone else sees a pin only if it's public *and* published.
A pin someone may not see is a 404, not a 403: a private spot's existence
is itself private.

Publishing is immediate (the chosen policy). Moderation is after the fact:
reports from `report_auto_hide_threshold` different people hide a pin
until an admin reviews it, and admins can hide, restore or remove any pin.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.types import utcnow
from app.knowledge.jurisdictions import STATE_NAMES
from app.knowledge.species_guides import GUIDES
from app.models.community import (
    PIN_HIDDEN,
    PIN_PUBLISHED,
    PIN_REMOVED,
    REPORT_OPEN,
    VISIBILITY_PRIVATE,
    VISIBILITY_PUBLIC,
    CatchPin,
    PinPhoto,
    PinReport,
    User,
)
from app.models.waterbody import Waterbody
from app.services import audit, counties, fish_id
from app.db.spatial import bbox_filter
from app.services.geo import haversine_km
from app.services.media import MediaStore, PhotoRejected, clean_photo, new_key

SPECIES_LABELS: dict[str, str] = {g.slug: g.common_name for g in GUIDES}
REPORT_REASONS = {
    "spam": "Spam or advertising",
    "inappropriate": "Inappropriate photo or text",
    "wrong_location": "Wrong or made-up location",
    "private_property": "Private property or no public access",
    "unsafe": "Unsafe or illegal",
    "other": "Something else",
}
# A pin this close to a lake's centre point is shown as "near <lake>". Lake
# centres, not shorelines, so this is a hint for the UI, not a claim.
LINK_RADIUS_KM = 3.0
MAX_LIST = 500


class PinError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


# ------------------------------------------------------------ permissions


def can_view(pin: CatchPin, user: User | None) -> bool:
    if user is not None and (user.id == pin.user_id or user.is_admin):
        return True
    return pin.visibility == VISIBILITY_PUBLIC and pin.status == PIN_PUBLISHED


def can_edit(pin: CatchPin, user: User | None) -> bool:
    """Owners edit their published pins. A hidden or removed pin is a
    moderation case: it stays as it was reported until a moderator decides,
    so the owner can't quietly rewrite it. Deleting it is still the
    owner's call (the delete endpoint, audited)."""
    return user is not None and user.id == pin.user_id and pin.status == PIN_PUBLISHED


def get_visible_pin(db: Session, pin_id: int, user: User | None) -> CatchPin:
    pin = db.get(CatchPin, pin_id)
    if pin is None or not can_view(pin, user):
        raise PinError(404, "No such pin.")
    return pin


# ---------------------------------------------------------------- inputs


@dataclass
class PinFields:
    latitude: float
    longitude: float
    title: str
    note: str | None
    species_slug: str | None
    species_other: str | None
    caught_on: date | None
    visibility: str


def _text(value: str | None, max_len: int) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if len(value) > max_len:
        raise PinError(422, f"Keep it under {max_len} characters.")
    return value


def claimed_species(species_slug: str | None, species_other: str | None) -> str | None:
    """The guide species a catch names, if any. "Other: largemouth bass" is
    the guide species, and is checked as one."""
    slug = (species_slug or "").strip() or None
    if slug is not None and slug not in SPECIES_LABELS:
        raise PinError(422, "Pick a species from the list, or use 'Other'.")
    norm = " ".join((species_other or "").lower().replace("-", " ").split())
    return slug or next((s for s, label in SPECIES_LABELS.items() if norm in (label.lower(), s.replace("-", " "))), None)


def validate(
    *,
    latitude: float,
    longitude: float,
    title: str,
    note: str | None,
    species_slug: str | None,
    species_other: str | None,
    caught_on: date | None,
    visibility: str,
) -> PinFields:
    if not (math.isfinite(latitude) and math.isfinite(longitude)):
        raise PinError(422, "That location isn't valid.")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise PinError(422, "That location isn't valid.")
    clean_title = " ".join((title or "").split())
    if not 3 <= len(clean_title) <= 80:
        raise PinError(422, "Give the pin a title of 3 to 80 characters.")
    slug = claimed_species(species_slug, species_other)
    if visibility not in (VISIBILITY_PUBLIC, VISIBILITY_PRIVATE):
        raise PinError(422, "Visibility is public or private.")
    if caught_on is not None:
        # A day of slack for time zones; nothing before modern record-keeping.
        if caught_on > (utcnow() + timedelta(days=1)).date() or caught_on.year < 1950:
            raise PinError(422, "That date doesn't look right.")
    return PinFields(
        latitude=round(latitude, 6),
        longitude=round(longitude, 6),
        title=clean_title,
        note=_text(note, 1000),
        species_slug=slug,
        species_other=None if slug else _text(species_other, 60),
        caught_on=caught_on,
        visibility=visibility,
    )


def nearest_waterbody(db: Session, lat: float, lng: float) -> Waterbody | None:
    # A cheap bounding box first (~0.03° ≈ 3.3 km), then exact distance.
    # bbox_filter puts this on the PostGIS index where there is one.
    d = 0.035
    rows = db.scalars(
        select(Waterbody).where(bbox_filter(db, lng - d, lat - d, lng + d, lat + d))
    ).all()
    best, best_km = None, LINK_RADIUS_KM
    for wb in rows:
        km = haversine_km(lat, lng, wb.latitude, wb.longitude)
        if km <= best_km:
            best, best_km = wb, km
    return best


# ---------------------------------------------------------------- photos


def _clean_all(uploads: list[bytes]) -> list:
    cleaned = []
    for i, data in enumerate(uploads, start=1):
        try:
            cleaned.append(clean_photo(data))
        except PhotoRejected as exc:
            raise PinError(422, f"Photo {i}: {exc}") from exc
    return cleaned


def _attach(db: Session, pin: CatchPin, cleaned: list, store: MediaStore) -> None:
    """Stores already-cleaned photos; if any store call fails, the ones
    already written are deleted so no orphan files are left behind."""
    limit = get_settings().max_photos_per_pin
    if len(pin.photos) + len(cleaned) > limit:
        raise PinError(422, f"A pin can have up to {limit} photos.")
    saved: list[str] = []
    try:
        start = max((p.position for p in pin.photos), default=-1) + 1
        for offset, photo in enumerate(cleaned):
            key = new_key(pin.id)
            store.save(key, photo.full, photo.thumb)
            saved.append(key)
            pin.photos.append(
                PinPhoto(
                    storage_key=key,
                    width=photo.width,
                    height=photo.height,
                    bytes=len(photo.full),
                    position=start + offset,
                )
            )
        db.flush()
    except Exception:
        for key in saved:
            store.delete(key)
        raise


# ---------------------------------------------------------- photo check


@dataclass(frozen=True)
class SpeciesCheck:
    verdict: fish_id.Verdict
    model: str


def check_species(species_slug: str | None, species_other: str | None, photo: bytes | None) -> SpeciesCheck | None:
    """The photo check on the fish a catch names (services/fish_id.py):
    None when it names none, or the check is off; PinError when the photo
    doesn't back the claim, with the reason and what the photo shows."""
    if species_slug is None and species_other is None:
        return None
    try:
        recognizer = fish_id.get_recognizer()
    except fish_id.FishIdUnavailable as exc:
        raise PinError(503, str(exc)) from exc
    if recognizer is None:
        return None
    if photo is None:
        raise PinError(422, "Add a photo of the fish: a catch that names a species needs one, and FishEye checks it.")
    verdict = fish_id.check_claim(recognizer.identify(photo), species_slug)
    if not verdict.accepted:
        raise PinError(422, verdict.message)
    return SpeciesCheck(verdict, recognizer.name)


def _record_check(pin: CatchPin, check: SpeciesCheck | None, photo: PinPhoto | None) -> None:
    v = check.verdict if check else None
    # "Other" only had to show a fish: nothing about its species was checked.
    pin.species_check = None if v is None or v.claimed is None else v.status
    pin.species_check_confidence = round(v.confidence, 3) if v else None
    pin.species_detected = v.detected if v else None
    pin.species_check_model = check.model if check else None
    pin.species_check_photo_id = photo.id if check and photo else None


def recheck_species(db: Session, pin: CatchPin, species_slug: str | None, species_other: str | None, store: MediaStore) -> None:
    """A changed species is checked against the pin's first photo."""
    first = pin.photos[0] if pin.photos else None
    path = store.path(first.storage_key, "full") if first else None
    check = check_species(species_slug, species_other, path.read_bytes() if path else None)
    _record_check(pin, check, first)


# ---------------------------------------------------------------- writes


def create_pin(db: Session, user: User, fields: PinFields, uploads: list[bytes], store: MediaStore) -> CatchPin:
    if len(uploads) > get_settings().max_photos_per_pin:
        raise PinError(422, f"A pin can have up to {get_settings().max_photos_per_pin} photos.")
    # Every photo is validated before anything is written, so one bad file
    # can't leave a half-created pin behind. The first is the catch's photo:
    # the one the species is checked against.
    cleaned = _clean_all(uploads)
    check = check_species(fields.species_slug, fields.species_other, cleaned[0].full if cleaned else None)
    lake = nearest_waterbody(db, fields.latitude, fields.longitude)
    pin = CatchPin(
        user_id=user.id,
        latitude=fields.latitude,
        longitude=fields.longitude,
        title=fields.title,
        note=fields.note,
        species_slug=fields.species_slug,
        species_other=fields.species_other,
        caught_on=fields.caught_on,
        visibility=fields.visibility,
        status=PIN_PUBLISHED,
        waterbody_id=lake.id if lake else None,
    )
    set_place(pin)
    db.add(pin)
    db.flush()
    if cleaned:
        _attach(db, pin, cleaned, store)
    _record_check(pin, check, pin.photos[0] if pin.photos else None)
    return pin


def add_photos(db: Session, pin: CatchPin, uploads: list[bytes], store: MediaStore) -> None:
    if not uploads:
        raise PinError(422, "Choose at least one photo.")
    limit = get_settings().max_photos_per_pin
    if len(pin.photos) + len(uploads) > limit:
        raise PinError(422, f"A pin can have up to {limit} photos.")
    _attach(db, pin, _clean_all(uploads), store)
    pin.updated_at = utcnow()


def delete_photo(db: Session, pin: CatchPin, photo_id: int, store: MediaStore) -> None:
    photo = next((p for p in pin.photos if p.id == photo_id), None)
    if photo is None:
        raise PinError(404, "No such photo.")
    if photo.id == pin.species_check_photo_id and (pin.species_slug or pin.species_other):
        raise PinError(
            409,
            "This is the photo that shows your fish, so it stays while the pin names a species. "
            "Change the fish to “Not sure” first, or delete the pin.",
        )
    key = photo.storage_key
    pin.photos.remove(photo)
    db.flush()
    store.delete(key)


def delete_pin(db: Session, pin: CatchPin, store: MediaStore) -> None:
    keys = [p.storage_key for p in pin.photos]
    db.delete(pin)
    db.flush()
    for key in keys:
        store.delete(key)


def photo_keys_of(user: User) -> list[str]:
    """Every stored photo of a user's pins — deleted once the account's rows are gone."""
    return [p.storage_key for pin in user.pins for p in pin.photos]


# ----------------------------------------------------------------- reads


def set_place(pin: CatchPin) -> None:
    """The pin's state and county, from where it is."""
    county = counties.county_at(pin.latitude, pin.longitude)
    pin.state_code = county.state if county else None
    pin.county_geoid = county.geoid if county else None
    pin.county_name = county.name if county else None


def fill_places(db: Session) -> int:
    """Gives pins saved before counties existed their state and county.
    Runs at startup; a no-op once every pin has one (or the outlines are
    missing). A pin outside every county is looked at again each time:
    there are few, and a lookup is cheap."""
    if counties.index() is None:
        return 0
    filled = 0
    for pin in db.scalars(select(CatchPin).where(CatchPin.state_code.is_(None))):
        set_place(pin)
        filled += pin.state_code is not None
    db.commit()
    return filled


def _visible(user: User | None, mine: bool):
    if mine:
        return CatchPin.user_id == (user.id if user else -1)
    visible = (CatchPin.visibility == VISIBILITY_PUBLIC) & (CatchPin.status == PIN_PUBLISHED)
    if user is not None:
        # Your own pins appear on your map too, private or not — but not
        # ones a moderator removed.
        visible = visible | ((CatchPin.user_id == user.id) & (CatchPin.status != PIN_REMOVED))
    return visible


@dataclass
class Place:
    id: str
    name: str
    count: int


def list_pins(
    db: Session,
    user: User | None,
    *,
    bbox: tuple[float, float, float, float] | None = None,
    species: str | None = None,
    mine: bool = False,
    state: str | None = None,
    county: str | None = None,
    lake: int | None = None,
    limit: int = 200,
) -> list[CatchPin]:
    if mine and user is None:
        return []
    q = select(CatchPin).options(selectinload(CatchPin.photos), selectinload(CatchPin.user))
    q = q.where(_visible(user, mine))
    if bbox is not None:
        west, south, east, north = bbox
        q = q.where(CatchPin.latitude.between(south, north), CatchPin.longitude.between(west, east))
    if species:
        q = q.where(CatchPin.species_slug == species)
    if state:
        q = q.where(CatchPin.state_code == state.upper())
    if county:
        q = q.where(CatchPin.county_geoid == county)
    if lake is not None:
        # 0: the county's pins that aren't at a mapped lake.
        q = q.where(CatchPin.waterbody_id == lake if lake else CatchPin.waterbody_id.is_(None))
    q = q.order_by(CatchPin.created_at.desc(), CatchPin.id.desc()).limit(min(max(limit, 1), MAX_LIST))
    return list(db.scalars(q).all())


NOT_AT_A_LAKE = "Not at a mapped lake"


def places(
    db: Session,
    user: User | None,
    *,
    state: str | None = None,
    county: str | None = None,
    species: str | None = None,
    mine: bool = False,
) -> list[Place]:
    """One level down from where the angler is browsing, with how many
    catches each has: states; a state's counties; a county's lakes (and,
    as lake 0, its pins that aren't at a mapped lake). Counted over the
    pins this user may see, so a private pin never shows up as a count."""
    if mine and user is None:
        return []
    where = [_visible(user, mine)]
    if species:
        where.append(CatchPin.species_slug == species)
    n = func.count(CatchPin.id)
    if county:
        where.append(CatchPin.county_geoid == county)
        rows = db.execute(
            select(CatchPin.waterbody_id, Waterbody.name, n)
            .outerjoin(Waterbody, Waterbody.id == CatchPin.waterbody_id)
            .where(*where)
            .group_by(CatchPin.waterbody_id, Waterbody.name)
        ).all()
        out = [Place(str(wid or 0), name or NOT_AT_A_LAKE, c) for wid, name, c in rows]
        # Lakes by catches, then name; "not at a lake" last.
        return sorted(out, key=lambda p: (p.id == "0", -p.count, p.name))
    if state:
        where.append(CatchPin.state_code == state.upper())
        where.append(CatchPin.county_geoid.is_not(None))
        rows = db.execute(
            select(CatchPin.county_geoid, CatchPin.county_name, n)
            .where(*where)
            .group_by(CatchPin.county_geoid, CatchPin.county_name)
        ).all()
        return sorted((Place(g, name or g, c) for g, name, c in rows), key=lambda p: (-p.count, p.name))
    where.append(CatchPin.state_code.is_not(None))
    rows = db.execute(select(CatchPin.state_code, n).where(*where).group_by(CatchPin.state_code)).all()
    return sorted((Place(code, STATE_NAMES.get(code, code), c) for code, c in rows), key=lambda p: (-p.count, p.name))


def species_label(pin: CatchPin) -> str | None:
    if pin.species_slug:
        return SPECIES_LABELS.get(pin.species_slug, pin.species_slug)
    return pin.species_other


# ------------------------------------------------------------- reporting


def open_report_count(db: Session, pin_id: int) -> int:
    return db.scalar(
        select(func.count(PinReport.id)).where(PinReport.pin_id == pin_id, PinReport.status == REPORT_OPEN)
    ) or 0


def report_pin(db: Session, pin: CatchPin, reporter: User, reason: str, detail: str | None) -> bool:
    """Files a report. Returns True if this report hid the pin."""
    if reason not in REPORT_REASONS:
        raise PinError(422, "Pick a reason.")
    if pin.user_id == reporter.id:
        raise PinError(422, "You can't report your own pin.")
    if pin.visibility != VISIBILITY_PUBLIC or pin.status == PIN_REMOVED:
        raise PinError(404, "No such pin.")
    existing = db.scalar(
        select(PinReport).where(PinReport.pin_id == pin.id, PinReport.reporter_id == reporter.id)
    )
    if existing is not None:
        raise PinError(409, "You've already reported this pin. A moderator will look at it.")
    db.add(PinReport(pin_id=pin.id, reporter_id=reporter.id, reason=reason, detail=_text(detail, 500)))
    db.flush()
    threshold = get_settings().report_auto_hide_threshold
    if pin.status == PIN_PUBLISHED and open_report_count(db, pin.id) >= threshold:
        pin.status = PIN_HIDDEN
        pin.status_reason = "reports"
        audit.record(db, None, "pin.auto_hidden", "pin", pin.id, open_reports=threshold)
        return True
    return False
