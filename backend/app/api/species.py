"""GET /api/species/guides — how to catch each species (app/knowledge/species_guides.py).
GET /api/species/handbook — what applies to every fish (app/knowledge/angling_handbook.py).
GET /api/species/questions — the question library (app/knowledge/angling_qa.py).
GET /api/species/photos — a real photo per species, with credit (services/species_photos.py)."""
from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from app.knowledge import angling_qa
from app.knowledge.angling_handbook import CATEGORIES, TOPICS
from app.knowledge.species_guides import (
    GENERAL_SUMMARIES,
    GUIDES,
    ONLY_IN_STATE,
    TPWD_LIMITS_URL,
    Source,
    SpeciesGuide,
    get_guide,
    sources_for,
)
from app.schemas.species_guide import (
    GuideSourceOut,
    HandbookTopicOut,
    QuestionOut,
    SpeciesGuideOut,
    SpeciesPhotoOut,
    TackleSetupOut,
)
from app.services import species_photos

router = APIRouter(prefix="/species", tags=["species"])


def source_out(s: Source) -> GuideSourceOut:
    return GuideSourceOut(label=s.label, url=s.url, kind=s.kind)


def _sources(ids: tuple[str, ...]) -> list[GuideSourceOut]:
    return [source_out(s) for s in sources_for(ids)]


def _unique_sources(ids: tuple[str, ...]) -> list[GuideSourceOut]:
    """One entry per page: the same page can be registered under two ids."""
    by_url = {s.url: s for s in reversed(sources_for(ids))}
    return [source_out(s) for s in reversed(list(by_url.values()))]


def to_out(guide: SpeciesGuide) -> SpeciesGuideOut:
    return SpeciesGuideOut(
        slug=guide.slug,
        common_name=guide.common_name,
        scientific_name=guide.scientific_name,
        role=guide.role,
        difficulty=guide.difficulty,
        summary=guide.summary,
        summary_general=GENERAL_SUMMARIES.get(guide.slug),
        only_in_state=ONLY_IN_STATE.get(guide.slug),
        diet=guide.diet,
        diet_type=guide.diet_type,
        where_and_when=list(guide.where_and_when),
        live_baits=list(guide.live_baits),
        lures=list(guide.lures),
        setups=[
            TackleSetupOut(
                name=s.name,
                use_when=s.use_when,
                method=s.method,
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
        habitat=list(guide.habitat),
        habits=list(guide.habits),
        why_these_baits=list(guide.why_these_baits),
        eating=list(guide.eating),
        how_to_get=list(guide.how_to_get),
        bait_for=list(guide.bait_for),
        legal_notes=list(guide.legal_notes),
        legal_notes_region="TX",
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


@router.get("/handbook", response_model=list[HandbookTopicOut])
def list_handbook() -> list[HandbookTopicOut]:
    """In page order: by category (CATEGORIES' order), then as written."""
    order = {c: i for i, c in enumerate(CATEGORIES)}
    ranked = sorted(enumerate(TOPICS), key=lambda pair: (order[pair[1].category], pair[0]))
    return [
        HandbookTopicOut(
            id=t.id,
            category=t.category,
            category_label=CATEGORIES[t.category],
            title=t.title,
            body=list(t.body),
            region=t.region,
            sources=_sources(t.source_ids),
        )
        for _, t in ranked
    ]


@router.get("/questions", response_model=list[QuestionOut])
def list_questions(lang: str = "en") -> list[QuestionOut]:
    """In page order, in Chinese for `lang=zh` and in English otherwise (the
    library has only those two)."""
    zh = lang == "zh"
    order = {c: i for i, c in enumerate(angling_qa.CATEGORIES)}
    ranked = sorted(enumerate(angling_qa.ITEMS), key=lambda pair: (order[pair[1].category], pair[0]))
    return [
        QuestionOut(
            id=i.id,
            category=i.category,
            category_label=angling_qa.CATEGORIES[i.category]["zh" if zh else "en"],
            question=i.question_zh if zh else i.question,
            short=i.short_zh if zh else i.short,
            body=i.body_zh if zh else i.body,
            basis=i.basis,
            sources=_unique_sources(i.source_ids),
        )
        for _, i in ranked
    ]


@router.get("/questions/sources", response_model=list[GuideSourceOut])
def list_question_sources() -> list[GuideSourceOut]:
    """Each source the library cites, once, for /sources."""
    ids = list(dict.fromkeys(s for i in angling_qa.ITEMS for s in i.source_ids))
    return _unique_sources(tuple(ids))


@router.get("/photos", response_model=dict[str, SpeciesPhotoOut | None])
def list_species_photos() -> dict[str, SpeciesPhotoOut | None]:
    """Separate from /guides on purpose: the guides are local and instant,
    the photos come from Wikipedia and may be slow or missing. A page can
    render the guides first and add photos when (and if) they arrive."""
    return {
        slug: SpeciesPhotoOut(**asdict(photo)) if photo else None
        for slug, photo in species_photos.get_photos().items()
    }
