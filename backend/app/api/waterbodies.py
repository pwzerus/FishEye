from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db
from app.db.spatial import bbox_filter, radius_filter, radius_is_exact
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
    """Lakes matching the filters, verified ones first.

    When more match than `limit`, the ones kept are the LARGEST (by
    `extent_km2`), not the first alphabetically. This matters at national
    scale: a map view a few degrees wide over Minnesota matches ~150,000
    lakes, and "the first 2000 by name" would be a random-looking scatter of
    the letters A to C. Verified lakes are never displaced by it — they are
    what this app actually knows something about, and there are few.

    The limit is applied in SQL. It used to be applied after loading every
    match into memory, which is invisible at Texas scale and a
    multi-second, multi-hundred-megabyte request at national scale.
    """

    def matching(*conditions):  # type: ignore[no-untyped-def]
        """The filtered query, before any tier split, ordering or limit."""
        stmt = select(Waterbody).join(Waterbody.state)
        if state_code:
            from app.models.waterbody import State

            stmt = stmt.where(State.code == state_code.upper())
        if species:
            stmt = stmt.join(Waterbody.species_links).join(WaterbodySpecies.species).where(
                Species.common_name.ilike(species)
            )
        if bbox:
            west, south, east, north = _parse_bbox(bbox)
            stmt = stmt.where(bbox_filter(db, west, south, east, north))
        if lat is not None and lng is not None:
            # PostGIS answers this exactly from its spatial index; SQLite gets
            # a coarse latitude-band prefilter and the haversine pass below
            # does the rest (app/db/spatial.py).
            stmt = stmt.where(radius_filter(db, lat, lng, radius_km))
        return stmt.where(*conditions)

    # A Python distance pass over the rows means the database cannot know how
    # many will survive it, so it cannot be asked for "the first N".
    refine = lat is not None and lng is not None and not radius_is_exact(db)

    def fetch(stmt, order_by, cap):  # type: ignore[no-untyped-def]
        stmt = stmt.order_by(*order_by)
        if cap is not None and not refine:
            stmt = stmt.limit(cap)
        rows = list(db.scalars(stmt).unique().all())
        if refine:
            rows = [
                w for w in rows if haversine_km(lat, lng, w.latitude, w.longitude) <= radius_km
            ]
        return rows

    by_name = (Waterbody.name,)
    by_size = (Waterbody.extent_km2.desc(), Waterbody.name)

    if tier == "verified":
        waterbodies = fetch(matching(Waterbody.data_tier == "verified"), by_name, limit)
    elif tier:
        waterbodies = fetch(matching(Waterbody.data_tier == tier), by_size, limit)
    else:
        # Two queries rather than one ordered by (tier, size): the composite
        # sort cannot use an index, so it would sort every match in view to
        # keep a handful. Split, each half has an index that serves it —
        # ix_waterbodies_verified_lat_lng and ix_waterbodies_extent.
        verified = fetch(matching(Waterbody.data_tier == "verified"), by_name, limit)
        room = limit - len(verified)
        others = (
            fetch(matching(Waterbody.data_tier != "verified"), by_size, room) if room > 0 else []
        )
        waterbodies = verified + others

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
