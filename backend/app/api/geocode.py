"""GET /api/geocode — the only thing in this app allowed to talk to
Nominatim (see app/services/geocoding.py for why: never call it from the
browser). The frontend's search box and "use my location" flow both go
through this endpoint, never the third-party one directly."""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api import rate_limits
from app.schemas.geocoding import GeocodeResultOut
from app.services import geocoding

router = APIRouter(prefix="/geocode", tags=["geocode"])


@router.get("", response_model=GeocodeResultOut, dependencies=[Depends(rate_limits.GEOCODE)])
def geocode_place(
    q: str = Query(..., min_length=2, description="Place name or address, e.g. 'Lake Fork, TX'"),
) -> GeocodeResultOut:
    try:
        result = geocoding.geocode(q)
    except geocoding.GeocodingUnavailable:
        # 503, not 404: this is "couldn't check", not "checked, no match" —
        # see geocoding.py's module docstring for why that distinction
        # matters to someone trying to find a lake.
        raise HTTPException(
            status_code=503,
            detail="Location search is temporarily unavailable. Please try again shortly.",
        )

    if result is None:
        raise HTTPException(status_code=404, detail=f"No location found for {q!r}.")

    return GeocodeResultOut(
        query=result.query,
        display_name=result.display_name,
        latitude=result.latitude,
        longitude=result.longitude,
    )
