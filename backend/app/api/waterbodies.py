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

router = APIRouter(prefix="/waterbodies", tags=["waterbodies"])


@router.get("", response_model=list[WaterbodyListItem])
def list_waterbodies(
    db: Session = Depends(get_db),
    state_code: str | None = Query(None, description="e.g. TX"),
    species: str | None = Query(None, description="common_name, e.g. 'Largemouth Bass'"),
    lat: float | None = Query(None),
    lng: float | None = Query(None),
    radius_km: float = Query(160.0, description="only used when lat/lng given"),
) -> list[Waterbody]:
    stmt = select(Waterbody).join(Waterbody.state)
    if state_code:
        from app.models.waterbody import State

        stmt = stmt.where(State.code == state_code.upper())
    if species:
        stmt = stmt.join(Waterbody.species_links).join(WaterbodySpecies.species).where(
            Species.common_name.ilike(species)
        )

    waterbodies = list(db.scalars(stmt).unique().all())

    if lat is not None and lng is not None:
        waterbodies = [
            w for w in waterbodies if haversine_km(lat, lng, w.latitude, w.longitude) <= radius_km
        ]

    return waterbodies


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
        access_points=list(wb.access_points),
        species=species_out,
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
