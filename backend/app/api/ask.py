"""Guide Q&A, in two steps (docs/adr/0023).

POST /api/ask           Search the reviewed fish guides and return the
                        passages that answer the question. No model call:
                        free, instant, open to everyone.
POST /api/ask/summary   Have the model write an answer from those passages.
                        Needs an account; a few per account per day
                        (services/ai_quota.py). Only a question the search
                        recognises as a fishing question gets this far.
GET  /api/ask/allowance Today's AI summaries left, for showing on the page.

The search is the product; the written answer is an extra on top of it.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import rate_limits
from app.api.auth_deps import optional_user, require_user, same_origin
from app.api.deps import get_db
from app.api.species import source_out
from app.knowledge import jurisdictions
from app.knowledge.species_guides import get_guide, sources_for
from app.models.community import User
from app.schemas.ask import (
    AiAllowanceOut,
    AskCitationOut,
    AskRequest,
    AskResponse,
    AskRetrievedOut,
    AskTraceOut,
)
from app.services import ai_quota
from app.services.rag import ask as rag_ask

router = APIRouter(prefix="/ask", tags=["ask"])

NOT_A_FISHING_QUESTION = (
    "AI summaries are for fishing questions the FishEye guides cover, and the guides "
    "don't cover this one. Nothing was used from today's allowance."
)


def _slug(payload: AskRequest) -> str | None:
    if not payload.species_slug:
        return None
    guide = get_guide(payload.species_slug)
    if guide is None:
        raise HTTPException(status_code=404, detail=f"no guide for {payload.species_slug!r}")
    return guide.slug


def _state(payload: AskRequest) -> str | None:
    if payload.state is None:
        return None
    code = jurisdictions.normalize(payload.state)
    if code is None:
        raise HTTPException(status_code=422, detail=f"unknown state {payload.state!r}")
    return code


def _allowance_out(db: Session, user: User | None) -> AiAllowanceOut:
    if user is None:
        return AiAllowanceOut(signed_in=False, limit=None, remaining=None)
    a = ai_quota.allowance(db, user)
    return AiAllowanceOut(signed_in=True, limit=a.limit, remaining=a.remaining)


def _response(result: rag_ask.AskResult, ai: AiAllowanceOut) -> AskResponse:
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
                region=p.region,
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
        ai=ai,
    )


@router.post("", response_model=AskResponse, dependencies=[Depends(rate_limits.SEARCH)])
def search_guides(
    payload: AskRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(optional_user),
) -> AskResponse:
    result = rag_ask.search_guides(payload.question, species_slug=_slug(payload), state=_state(payload))
    return _response(result, _allowance_out(db, user))


@router.get("/allowance", response_model=AiAllowanceOut)
def allowance(db: Session = Depends(get_db), user: User | None = Depends(optional_user)) -> AiAllowanceOut:
    return _allowance_out(db, user)


@router.post(
    "/summary",
    response_model=AskResponse,
    # require_user before the LLM budget, so a signed-out request is turned
    # away without using anyone's allowance (FastAPI runs it once per request).
    dependencies=[Depends(same_origin), Depends(require_user), Depends(rate_limits.LLM)],
)
def summarize(
    payload: AskRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> AskResponse:
    """In order, so that nothing is spent on a request that can't succeed:
    the question must be one the guides cover (a search, no model call),
    then a summary is reserved from today's allowance, then the model is
    called. A summary that doesn't come back model-written (the model was
    unreachable, or its answer failed validation and the guides were quoted
    instead) is given back, and so is one answered from the cache, which
    cost nothing.

    Like /advisor/explain, a model failure is not an error: the response is
    still 200, with `answer_source` "fallback" saying so."""
    slug, state = _slug(payload), _state(payload)
    if not rag_ask.search_guides(payload.question, species_slug=slug, state=state).citations:
        raise HTTPException(status_code=422, detail=NOT_A_FISHING_QUESTION)

    day = ai_quota.today()
    if not ai_quota.reserve(db, user, day):
        limit = ai_quota.allowance(db, user, day).limit
        raise HTTPException(
            status_code=429,
            detail=(
                f"You've used today's {limit} AI summaries. Searching the guides is still free; "
                "summaries come back tomorrow (UTC)."
            ),
        )

    result = rag_ask.ask(payload.question, species_slug=slug, state=state)
    if result.answer_source != rag_ask.ANSWER_LLM or result.trace.cache_hit:
        ai_quota.give_back(db, user, day)
    return _response(result, _allowance_out(db, user))
