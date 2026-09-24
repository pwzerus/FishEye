from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db
from app.models.waterbody import Species, Waterbody, WaterbodySpecies
from app.schemas.waterbody import (
    SpeciesDetail,
    SpeciesSummaryOut,
    WaterbodyDetail,
    WaterbodyListItem,
)
from app.services.geo import haversine_km
from app.services.reported_species import reported_species, reported_species_counts

router = APIRouter(prefix="/waterbodies", tags=["waterbodies"])


MAX_LIST_RESULTS = 5000


def _parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    """"west,south,east,north" — the order Leaflet's LatLngBounds
    .toBBoxString() produces, so the frontend can pass it through as-is."""
    try:
        west, south, east, north = (float(part) for part in bbox.split(","))
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="bbox must be 'west,south,east,north' as four numbers"
        ) from exc
    if not (south <= north and west <= east):
        raise HTTPException(status_code=422, detail="bbox has south > north or west > east")
    return west, south, east, north


@router.get("", response_model=list[WaterbodyListItem])
def list_waterbodies(
    db: Session = Depends(get_db),
    state_code: str | None = Query(None, description="e.g. TX"),
    species: str | None = Query(None, description="common_name, e.g. 'Largemouth Bass'"),
    lat: float | None = Query(None),
    lng: float | None = Query(None),
    radius_km: float = Query(160.0, description="only used when lat/lng given"),
    bbox: str | None = Query(
        None, description="map viewport as 'west,south,east,north' (Leaflet toBBoxString order)"
    ),
    tier: str | None = Query(None, description="'verified' or 'osm'; omit for both"),
    limit: int = Query(2000, ge=1, le=MAX_LIST_RESULTS),
) -> list[WaterbodyListItem]:
    stmt = select(Waterbody).join(Waterbody.state)
    if state_code:
        from app.models.waterbody import State

        stmt = stmt.where(State.code == state_code.upper())
    if species:
        stmt = stmt.join(Waterbody.species_links).join(WaterbodySpecies.species).where(
            Species.common_name.ilike(species)
        )
    if tier:
        stmt = stmt.where(Waterbody.data_tier == tier)
    if bbox:
        west, south, east, north = _parse_bbox(bbox)
        stmt = stmt.where(
            Waterbody.latitude.between(south, north),
            Waterbody.longitude.between(west, east),
        )
    if lat is not None and lng is not None:
        # Coarse bounding-box prefilter in SQL (1 degree of latitude is
        # ~111 km) so the exact haversine check below runs on a handful of
        # rows, not the whole statewide table.
        pad = radius_km / 111.0
        stmt = stmt.where(Waterbody.latitude.between(lat - pad, lat + pad))

    # Verified lakes first, so a capped result can never drop one of the
    # lakes this app actually knows something about in favour of an
    # OSM-only pond.
    stmt = stmt.order_by((Waterbody.data_tier != "verified"), Waterbody.name)

    waterbodies = list(db.scalars(stmt).unique().all())

    if lat is not None and lng is not None:
        waterbodies = [
            w for w in waterbodies if haversine_km(lat, lng, w.latitude, w.longitude) <= radius_km
        ]

    waterbodies = waterbodies[:limit]
    counts = reported_species_counts(db, (w.id for w in waterbodies))
    return [
        WaterbodyListItem(
            id=w.id,
            name=w.name,
            latitude=w.latitude,
            longitude=w.longitude,
            field_tested=w.field_tested,
            public_access_status=w.public_access_status,
            data_tier=w.data_tier,
            water_type=w.water_type,
            reported_species_count=counts.get(w.id, 0),
        )
        for w in waterbodies
    ]


@router.get("/{waterbody_id}", response_model=WaterbodyDetail)
def get_waterbody(waterbody_id: int, db: Session = Depends(get_db)) -> WaterbodyDetail:
    wb = db.get(
        Waterbody,
        waterbody_id,
        options=[selectinload(Waterbody.access_points), selectinload(Waterbody.species_links)],
    )
    if wb is None:
        raise HTTPException(status_code=404, detail="waterbody not found")

    species_out = [
        SpeciesSummaryOut(
            common_name=link.species.common_name,
            difficulty=link.species.difficulty,
            confidence=link.confidence,
            evidence=link.evidence,
            source_url=link.source_url,
            observed_at=link.observed_at,
        )
        for link in wb.species_links
    ]
    return WaterbodyDetail(
        id=wb.id,
        name=wb.name,
        latitude=wb.latitude,
        longitude=wb.longitude,
        access_summary=wb.access_summary,
        source_url=wb.source_url,
        source_updated_at=wb.source_updated_at,
        field_tested=wb.field_tested,
        public_access_status=wb.public_access_status,
        data_tier=wb.data_tier,
        water_type=wb.water_type,
        access_points=list(wb.access_points),
        species=species_out,
        reported_species=reported_species(db, wb.id, confirmed=(s.common_name for s in species_out)),
    )


@router.get("/{waterbody_id}/species", response_model=list[SpeciesDetail])
def get_waterbody_species(waterbody_id: int, db: Session = Depends(get_db)) -> list[Species]:
    wb = db.get(Waterbody, waterbody_id, options=[selectinload(Waterbody.species_links)])
    if wb is None:
        raise HTTPException(status_code=404, detail="waterbody not found")
    species_ids = [link.species_id for link in wb.species_links]
    if not species_ids:
        return []
    stmt = (
        select(Species)
        .where(Species.id.in_(species_ids))
        .options(selectinload(Species.conditions))
    )
    return list(db.scalars(stmt).all())
