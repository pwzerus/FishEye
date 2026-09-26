"""POST /api/ask — answer a question from the reviewed fish guides."""
from fastapi import APIRouter, HTTPException

from app.api.species import source_out
from app.knowledge.species_guides import get_guide, sources_for
from app.schemas.ask import (
    AskCitationOut,
    AskRequest,
    AskResponse,
    AskRetrievedOut,
    AskTraceOut,
)
from app.services.rag import ask as rag_ask

router = APIRouter(prefix="/ask", tags=["ask"])


@router.post("", response_model=AskResponse)
def ask_question(payload: AskRequest) -> AskResponse:
    """Like /advisor/explain, there's no error path for a model failure: a
    rejected or missing answer degrades to quoting the guides and still
    returns 200, with `answer_source` and `trace.outcome` saying so."""
    slug: str | None = None
    if payload.species_slug:
        guide = get_guide(payload.species_slug)
        if guide is None:
            raise HTTPException(status_code=404, detail=f"no guide for {payload.species_slug!r}")
        slug = guide.slug

    result = rag_ask.ask(payload.question, species_slug=slug)
    t = result.trace
    return AskResponse(
        question=result.question,
        answer=result.answer,
        answer_source=result.answer_source,
        citations=[
            AskCitationOut(
                id=p.id,
                species_slug=p.species_slug,
                species_name=p.species_name,
                section=p.section,
                title=p.title,
                excerpt=rag_ask.body_of(p),
                sources=[source_out(s) for s in sources_for(p.source_ids)],
            )
            for p in result.citations
        ],
        trace=AskTraceOut(
            trace_id=t.trace_id,
            retriever=t.retriever,
            routed_species=t.routed_species,
            retrieved=[AskRetrievedOut(**r) for r in t.retrieved],
            provider=t.provider,
            model=t.model,
            latency_ms=round(t.latency_ms, 2),
            prompt_tokens=t.prompt_tokens,
            completion_tokens=t.completion_tokens,
            estimated_cost_usd=round(t.estimated_cost_usd, 6),
            validation_attempts=t.validation_attempts,
            outcome=t.outcome,
            cache_hit=t.cache_hit,
        ),
    )
