"""GET /api/species/guides — how to catch each species (app/knowledge/species_guides.py)."""
from fastapi import APIRouter, HTTPException

from app.knowledge.species_guides import (
    GUIDES,
    TPWD_LIMITS_URL,
    SpeciesGuide,
    get_guide,
    sources_for,
)
from app.schemas.species_guide import GuideSourceOut, SpeciesGuideOut, TackleSetupOut

router = APIRouter(prefix="/species", tags=["species"])


def _sources(ids: tuple[str, ...]) -> list[GuideSourceOut]:
    return [GuideSourceOut(label=s.label, url=s.url, kind=s.kind) for s in sources_for(ids)]


def to_out(guide: SpeciesGuide) -> SpeciesGuideOut:
    return SpeciesGuideOut(
        slug=guide.slug,
        common_name=guide.common_name,
        scientific_name=guide.scientific_name,
        role=guide.role,
        difficulty=guide.difficulty,
        summary=guide.summary,
        diet=guide.diet,
        where_and_when=list(guide.where_and_when),
        live_baits=list(guide.live_baits),
        lures=list(guide.lures),
        setups=[
            TackleSetupOut(
                name=s.name,
                use_when=s.use_when,
                rod=s.rod,
                reel=s.reel,
                line=s.line,
                terminal=s.terminal,
                sources=_sources(s.source_ids),
            )
            for s in guide.setups
        ],
        tips=list(guide.tips),
        identification=list(guide.identification),
        how_to_get=list(guide.how_to_get),
        bait_for=list(guide.bait_for),
        legal_notes=list(guide.legal_notes),
        limits_url=TPWD_LIMITS_URL,
        sources=_sources(guide.source_ids),
    )


@router.get("/guides", response_model=list[SpeciesGuideOut])
def list_guides() -> list[SpeciesGuideOut]:
    # Sport fish first (beginner-friendly ones leading), bait fish last.
    order = {"beginner": 0, "intermediate": 1, "advanced": 2, None: 3}
    ranked = sorted(GUIDES, key=lambda g: (g.role != "sport", order[g.difficulty], g.common_name))
    return [to_out(g) for g in ranked]


@router.get("/guides/{slug}", response_model=SpeciesGuideOut)
def get_species_guide(slug: str) -> SpeciesGuideOut:
    guide = get_guide(slug)
    if guide is None:
        raise HTTPException(status_code=404, detail=f"no guide for {slug!r}")
    return to_out(guide)
