"""/api/shops — bait and tackle shops in the map's view (models/shop.py)."""
from __future__ import annotations

import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import rate_limits
from app.api.deps import get_db
from app.api.waterbodies import _parse_bbox
from app.models.shop import TackleShop
from app.schemas.shop import ShopOut
from app.services.geo import haversine_km

router = APIRouter(prefix="/shops", tags=["shops"], dependencies=[Depends(rate_limits.MAP)])

MAX_SHOPS = 500
_OSM_TYPES = {"n": "node", "w": "way"}


def osm_url(ref: str) -> str:
    return f"https://www.openstreetmap.org/{_OSM_TYPES[ref[0]]}/{ref[1:]}"


def _out(s: TackleShop, distance_km: float | None = None) -> ShopOut:
    return ShopOut(
        id=s.id,
        name=s.name,
        kind=s.kind,
        latitude=s.latitude,
        longitude=s.longitude,
        address=s.address,
        phone=s.phone,
        website=s.website,
        opening_hours=s.opening_hours,
        osm_url=osm_url(s.osm_ref),
        distance_km=round(distance_km, 2) if distance_km is not None else None,
    )


@router.get("/near", response_model=list[ShopOut])
def nearest_shops(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=40, gt=0, le=100),
    limit: int = Query(default=3, ge=1, le=10),
    db: Session = Depends(get_db),
) -> list[ShopOut]:
    """The shops closest to a point (a lake), nearest first, in a straight
    line: for "where do I get bait on the way"."""
    dlat = radius_km / 111.32
    dlng = radius_km / (111.32 * max(math.cos(math.radians(lat)), 0.01))
    rows = db.scalars(
        select(TackleShop).where(
            TackleShop.latitude.between(lat - dlat, lat + dlat),
            TackleShop.longitude.between(lng - dlng, lng + dlng),
        )
    )
    near = sorted(((haversine_km(lat, lng, s.latitude, s.longitude), s) for s in rows), key=lambda t: t[0])
    return [_out(s, km) for km, s in near if km <= radius_km][:limit]


@router.get("", response_model=list[ShopOut])
def list_shops(
    bbox: str = Query(..., description="west,south,east,north"),
    # The map shows one state at a time; shops across the border are masked.
    state_code: str | None = Query(default=None, min_length=2, max_length=2),
    limit: int = Query(default=MAX_SHOPS, ge=1, le=MAX_SHOPS),
    db: Session = Depends(get_db),
) -> list[ShopOut]:
    west, south, east, north = _parse_bbox(bbox)
    query = select(TackleShop).where(
        TackleShop.latitude.between(south, north),
        TackleShop.longitude.between(west, east),
    )
    if state_code:
        query = query.where(TackleShop.state_code == state_code.upper())
    return [_out(s) for s in db.scalars(query.order_by(TackleShop.id).limit(limit))]
