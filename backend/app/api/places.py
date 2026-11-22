"""GET /api/places/suggest — place names as you type, from FishEye's own list
of US places (services/place_suggest.py). Nothing outside is asked, unlike
/api/geocode, so the search box may ask on every keystroke."""
from fastapi import APIRouter, Depends, Query, Response

from app.api import rate_limits
from app.schemas.geocoding import PlaceSuggestionOut
from app.services import place_suggest

router = APIRouter(prefix="/places", tags=["places"])

# The list changes only with a deploy: a browser may keep an answer a day.
CACHE_SECONDS = 24 * 60 * 60


@router.get("/suggest", response_model=list[PlaceSuggestionOut], dependencies=[Depends(rate_limits.SUGGEST)])
def suggest_places(
    response: Response,
    q: str = Query(..., min_length=1, max_length=100, description="What's been typed so far, e.g. 'aus' or '787'"),
    state: str | None = Query(None, min_length=2, max_length=2, description="Only this state's places (typed after the name)"),
    prefer: str | None = Query(None, min_length=2, max_length=2, description="The state the map is in: its places first"),
    lat: float | None = Query(None, ge=-90, le=90, description="Where the map is looking: nearer places first"),
    lon: float | None = Query(None, ge=-180, le=180),
    limit: int = Query(6, ge=1, le=10),
) -> list[PlaceSuggestionOut]:
    near = (lat, lon) if lat is not None and lon is not None else None
    found = place_suggest.suggest(q, state=state, prefer_state=prefer.upper() if prefer else None, near=near, limit=limit)
    response.headers["Cache-Control"] = f"public, max-age={CACHE_SECONDS}"
    return [
        PlaceSuggestionOut(label=p.label, name=p.name, state=p.state, kind=p.kind, latitude=p.latitude, longitude=p.longitude)
        for p in found
    ]
