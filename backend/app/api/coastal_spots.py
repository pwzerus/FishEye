"""/api/coastal-spots: saltwater fishing piers, jetties, mapped fishing spots
and boat ramps (models/coastal_spot.py), in the map's view or by state."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import rate_limits
from app.api.deps import get_db
from app.api.shops import osm_url
from app.api.waterbodies import _parse_bbox
from app.data_import.cdfw_piers import PAGE as CDFW_PIERS_PAGE
from app.models.coastal_spot import KINDS, CoastalSpot
from app.schemas.coastal_spot import CoastalSpotOut

router = APIRouter(prefix="/coastal-spots", tags=["coastal spots"], dependencies=[Depends(rate_limits.MAP)])

MAX_SPOTS = 800


def _out(s: CoastalSpot) -> CoastalSpotOut:
    osm = osm_url(s.osm_ref) if s.osm_ref else None
    return CoastalSpotOut(
        id=s.id, name=s.name, kind=s.kind, coast=s.coast, latitude=s.latitude, longitude=s.longitude,
        state_code=s.state_code, fishing_tagged=s.fishing_tagged, fee=s.fee, opening_hours=s.opening_hours,
        lit=s.lit, operator=s.operator, website=s.website, no_license=s.no_license, license_note=s.license_note,
        source=s.source, source_url=CDFW_PIERS_PAGE if s.source == "cdfw" else osm or "", osm_url=osm,
    )


@router.get("", response_model=list[CoastalSpotOut])
def list_spots(
    bbox: str | None = Query(default=None, description="west,south,east,north"),
    state_code: str | None = Query(default=None, min_length=2, max_length=2),
    kind: list[str] | None = Query(default=None, description="pier, jetty, fishing_spot, boat_ramp"),
    limit: int = Query(default=MAX_SPOTS, ge=1, le=MAX_SPOTS),
    db: Session = Depends(get_db),
) -> list[CoastalSpotOut]:
    """The spots in a box, or a state's (named ones first), at most `limit`."""
    query = select(CoastalSpot)
    if bbox:
        west, south, east, north = _parse_bbox(bbox)
        query = query.where(CoastalSpot.latitude.between(south, north), CoastalSpot.longitude.between(west, east))
    if state_code:
        query = query.where(CoastalSpot.state_code == state_code.upper())
    kinds = [k for k in (kind or []) if k in KINDS]
    if kinds:
        query = query.where(CoastalSpot.kind.in_(kinds))
    # Official public piers, then fishing-tagged and named spots: they are
    # what a list or a crowded map should show when there are more than `limit`.
    query = query.order_by(
        CoastalSpot.no_license.desc(), CoastalSpot.fishing_tagged.desc(), CoastalSpot.name.is_(None), CoastalSpot.id,
    )
    return [_out(s) for s in db.scalars(query.limit(limit))]
