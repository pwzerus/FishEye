import re
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api import rate_limits
from app.api.deps import get_db
from app.db.spatial import bbox_filter, radius_filter, radius_is_exact
from app.models.waterbody import Species, SpeciesEvidence, Waterbody, WaterbodySource, WaterbodySpecies
from app.schemas.waterbody import (
    DatasetSourceOut,
    EvidenceItemOut,
    AgencyProfileOut,
    LakeMatchOut,
    SpeciesDetail,
    SpeciesSummaryOut,
    WaterbodyDetail,
    WaterbodyListItem,
)
from app.services import counties
from app.services.geo import haversine_km
from app.services.reported_species import reported_species, reported_species_counts

router = APIRouter(prefix="/waterbodies", tags=["waterbodies"], dependencies=[Depends(rate_limits.MAP)])


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


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


# Declared before /{waterbody_id}, which would otherwise take "search" for an id.
@router.get("/search", response_model=list[LakeMatchOut])
def search_waterbodies(
    q: str = Query(..., min_length=2, max_length=80, description="a lake's name, e.g. 'Freeman Lake'"),
    state_code: str | None = Query(None, description="the state being looked at; its lakes come first"),
    lat: float | None = Query(None, description="where the map is looking; nearer lakes come first"),
    lng: float | None = Query(None),
    limit: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db),
) -> list[LakeMatchOut]:
    """Lakes FishEye has, by name, for the search box. A place geocoder
    sends "Freeman Lake" to whichever Freeman Lake it ranks first (one in
    Kentucky, for someone looking at Georgia: the 2026-10-29 walkthrough).
    Best first: the whole name, then names that start with the words, then
    names holding them all; within each, the state being looked at, the
    nearest to where the map is, the lakes FishEye verified, the biggest.
    Each carries its county: Georgia alone has four Freeman Lakes."""
    words = _words(q)
    if not words:
        return []
    stmt = select(Waterbody).join(Waterbody.state).options(selectinload(Waterbody.state))
    for word in words:
        stmt = stmt.where(func.lower(Waterbody.name).contains(word))
    # Enough to rank; a name every lake shares ("lake") is narrowed by the rest.
    candidates = db.scalars(stmt.order_by(Waterbody.extent_km2.desc()).limit(200)).all()
    wanted = " ".join(words)
    picked = (state_code or "").upper()

    def rank(w: Waterbody) -> tuple[int, int, float, int, float]:
        name = " ".join(_words(w.name))
        how = 0 if name == wanted else 1 if name.startswith(wanted) else 2
        away = haversine_km(lat, lng, w.latitude, w.longitude) if lat is not None and lng is not None else 0.0
        return (how, w.state.code != picked, away, w.data_tier != "verified", -w.extent_km2)

    def county(w: Waterbody) -> str | None:
        c = counties.county_at(w.latitude, w.longitude)
        return c.name if c else None

    return [
        LakeMatchOut(
            id=w.id, name=w.name, latitude=w.latitude, longitude=w.longitude,
            state_code=w.state.code, state_name=w.state.name, data_tier=w.data_tier,
            county=county(w),
        )
        for w in sorted(candidates, key=rank)[:limit]
    ]


@router.get("/{waterbody_id}", response_model=WaterbodyDetail)
def get_waterbody(waterbody_id: int, db: Session = Depends(get_db)) -> WaterbodyDetail:
    wb = db.get(
        Waterbody,
        waterbody_id,
        options=[
            selectinload(Waterbody.access_points),
            selectinload(Waterbody.species_links),
            selectinload(Waterbody.agency_profile),
            selectinload(Waterbody.fish_attractors),
            selectinload(Waterbody.species_evidence).selectinload(SpeciesEvidence.source_record),
            selectinload(Waterbody.dataset_links).selectinload(WaterbodySource.source_record),
            selectinload(Waterbody.state),
        ],
    )
    if wb is None:
        raise HTTPException(status_code=404, detail="waterbody not found")

    items: dict[int, list[EvidenceItemOut]] = defaultdict(list)
    for e in sorted(wb.species_evidence, key=lambda e: (-(e.year or 0), e.kind)):
        items[e.species_id].append(EvidenceItemOut(
            evidence=e.evidence, source_url=e.source_url, kind=e.kind, year=e.year,
            publisher=e.source_record.publisher if e.source_record else None,
        ))
    species_out = [
        SpeciesSummaryOut(
            common_name=link.species.common_name,
            difficulty=link.species.difficulty,
            confidence=link.confidence,
            evidence=link.evidence,
            source_url=link.source_url,
            observed_at=link.observed_at,
            evidence_items=items.get(link.species_id, []),
        )
        for link in sorted(wb.species_links, key=lambda link: link.species.common_name)
    ]
    box = (wb.bbox_south, wb.bbox_west, wb.bbox_north, wb.bbox_east)
    return WaterbodyDetail(
        id=wb.id,
        name=wb.name,
        latitude=wb.latitude,
        longitude=wb.longitude,
        state_code=wb.state.code,
        bounds=list(box) if all(v is not None for v in box) else None,
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
        agency_profile=AgencyProfileOut.model_validate(wb.agency_profile) if wb.agency_profile else None,
        # A closed lake shows no places to fish, official or not (PRD §12).
        fish_attractors=[] if wb.public_access_status == "closed" else list(wb.fish_attractors),
        official_name=wb.official_name,
        public_land=wb.public_land,
        public_land_name=wb.public_land_name,
        public_land_manager=wb.public_land_manager,
        data_credit=AGENCY_CREDITS.get(wb.agency_profile.agency) if wb.agency_profile else None,
        sources=_sources(wb),
    )


# Facts from a state agency are credited to it next to the facts
# (data-sourcing rule 7; docs/data-sources.md).
AGENCY_CREDITS = {
    "tpwd": "Data: Texas Parks and Wildlife Department",
    "ga_wrd": "Data: Georgia DNR Wildlife Resources Division",
    "cdfw": "Data: California Department of Fish and Wildlife",
}


def _sources(wb: Waterbody) -> list[DatasetSourceOut]:
    """Every dataset behind this lake, once each: the lake's own (CDFW's
    lake layer, stocking, PAD-US), then those behind its species."""
    seen: dict[int, DatasetSourceOut] = {}
    records = [link.source_record for link in wb.dataset_links] + [
        e.source_record for e in wb.species_evidence if e.source_record is not None
    ]
    for r in records:
        if r.id not in seen:
            seen[r.id] = DatasetSourceOut(
                title=r.title or r.publisher, publisher=r.publisher, licence=r.licence_name,
                citation=r.citation, url=r.url,
            )
    return list(seen.values())


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
