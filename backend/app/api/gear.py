"""GET /api/gear — what to buy, with a photo of each thing (app/knowledge/gear.py);
POST /api/gear/identify — what a photo of some gear shows (services/gear_id.py)."""
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from app.api import rate_limits
from app.api.auth_deps import optional_user, same_origin
from app.api.rate_limits import client_ip
from app.core.config import get_settings
from app.core.security import RateLimiter
from app.knowledge import gear
from app.models.community import User
from app.schemas.gear import GearCandidateOut, GearCategoryOut, GearIdOut, GearItemOut, GearOut, GearPhotoOut
from app.services import gear_id
from app.services.media import PhotoRejected, clean_photo

router = APIRouter(prefix="/gear", tags=["gear"])

# A reading is a second or two of the server's CPU (the model runs here; no
# paid API is called). Signed in, a generous hourly allowance; signed out, a
# few a day from one address and a daily total for everyone signed out, so a
# script can't keep the CPU busy.
gear_id_by_user = RateLimiter(limit=60, window_seconds=60 * 60)
gear_id_trial_by_ip = RateLimiter(limit=10, window_seconds=24 * 60 * 60)
gear_id_trial_everyone = RateLimiter(limit=500, window_seconds=24 * 60 * 60)
TRIAL_USED = "You've used today's free gear photos. Sign in (it's free) to check more."
TRIAL_FULL = "Free gear photos are at today's limit. Sign in (it's free) to keep checking."
CANDIDATES = 3


def item_out(i: gear.GearItem) -> GearItemOut:
    p = i.photo
    return GearItemOut(
        id=i.id, name=i.name, category=i.category, what=i.what, tip=i.tip, topic=i.topic,
        fish=list(i.fish), first_kit=i.first_kit,
        photo=GearPhotoOut(
            url=p.url, width=p.width, height=p.height, author=p.author, license=p.licence,
            license_url=p.licence_url, file_page=p.page,
        ) if p else None,
    )


@router.get("", response_model=GearOut)
def list_gear() -> GearOut:
    return GearOut(
        categories=[GearCategoryOut(id=c, label=label) for c, label in gear.CATEGORIES.items()],
        items=[item_out(i) for i in gear.items()],
        camera=gear_id.installed(),
    )


def _allow(request: Request, user: User | None) -> None:
    """Refused before any work once the allowance is used."""
    if not get_settings().rate_limits_enabled:
        return
    if user is not None:
        key = str(user.id)
        wait = gear_id_by_user.blocked_for(key)
        if wait > 0:
            raise HTTPException(status_code=429, detail="You're doing that a lot. Try again later.",
                                headers={"Retry-After": str(int(wait) + 1)})
        gear_id_by_user.hit(key)
        return
    ip = client_ip(request)
    own = gear_id_trial_by_ip.blocked_for(ip)
    shared = gear_id_trial_everyone.blocked_for(rate_limits.EVERYONE)
    if own > 0 or shared > 0:
        raise HTTPException(status_code=429, detail=TRIAL_USED if own > 0 else TRIAL_FULL,
                            headers={"Retry-After": str(int(max(own, shared)) + 1)})
    gear_id_trial_by_ip.hit(ip)
    gear_id_trial_everyone.hit(rate_limits.EVERYONE)


@router.post("/identify", response_model=GearIdOut, dependencies=[Depends(same_origin)])
def identify_gear(
    request: Request,
    photo: UploadFile = File(...),
    user: User | None = Depends(optional_user),
) -> GearIdOut:
    """The likeliest items of /gear for a photo, or that it shows no gear.
    The photo is read and forgotten: nothing is stored."""
    _allow(request, user)
    cap = get_settings().max_photo_bytes
    data = photo.file.read(cap + 1)  # one byte past the cap is enough to know
    if len(data) > cap:
        raise HTTPException(status_code=413, detail=f"Photos can be up to {cap // (1024 * 1024)} MB.")
    try:
        cleaned = clean_photo(data)
    except PhotoRejected as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        recognizer = gear_id.get_recognizer()
    except gear_id.GearIdUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if recognizer is None:
        return GearIdOut(available=False, model=None, gear_probability=None, sure=False, candidates=[],
                         not_gear=None, message=None)
    reading = recognizer.read(cleaned.full)
    shown = reading.candidates[:CANDIDATES] if reading.is_gear else ()
    return GearIdOut(
        available=True,
        model=reading.model,
        gear_probability=round(reading.gear_probability, 3),
        sure=reading.sure,
        candidates=[
            GearCandidateOut(id=c.id, name=gear.ITEM_BY_ID[c.id].name, category=gear.ITEM_BY_ID[c.id].category,
                             probability=round(c.probability, 3))
            for c in shown
        ],
        # What it looks like instead, only when it isn't gear at all (not when
        # it is gear too unclear to name).
        not_gear=(reading.not_gear.removeprefix("x-")
                  if reading.not_gear and reading.gear_probability < gear_id.POLICY.min_gear else None),
        message=gear_id.message(reading),
    )
