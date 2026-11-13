"""Guide Q&A, in two steps (docs/adr/0023).

POST /api/ask           Search the reviewed fish guides and return the
                        passages that answer the question. No model call:
                        free, instant, open to everyone.
POST /api/ask/summary   Have the model write an answer: from those passages,
                        and from its own knowledge where the guides stop.
                        Needs an account; one a day on a free account, no
                        limit on Plus (services/ai_quota.py). Only a fishing
                        question gets this far.
GET  /api/ask/allowance Today's AI summaries left, for showing on the page.

The search is the product; the written answer is an extra on top of it.
"""
from dataclasses import replace

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
    AskLakesOut,
    AskRequest,
    AskResponse,
    AskRetrievedOut,
    AskTraceOut,
)
from app.services import ai_budget, ai_quota, ask_misses
from app.services.rag import ask as rag_ask
from app.services.rag import lake_facts, replies, site_help

router = APIRouter(prefix="/ask", tags=["ask"])

NOT_A_FISHING_QUESTION = (
    "AI answers are for fishing questions, and this doesn't look like one. "
    "Nothing was used from today's allowance."
)

# What the search found that an AI answer can add to: the guides' passages,
# or nothing for a fishing question they don't cover (since 2026-11-12 the
# model answers those from its own knowledge, services/rag/ask.py). Not a
# question that isn't about fishing, nor one the lake data or a page of the
# site answers: the model knows nothing of FishEye's lakes.
_AI_CAN_ADD_TO = {rag_ask.OUTCOME_NO_MATCH, rag_ask.OUTCOME_UNGUIDED_FISH, rag_ask.OUTCOME_OTHER_STATE}


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
    enabled = ai_budget.available()
    if user is None:
        return AiAllowanceOut(signed_in=False, limit=None, remaining=None, enabled=enabled)
    a = ai_quota.allowance(db, user)
    return AiAllowanceOut(signed_in=True, limit=a.limit, remaining=a.remaining, enabled=enabled, plus=a.plus)


def _response(
    result: rag_ask.AskResult,
    ai: AiAllowanceOut,
    state: str | None = None,
    lakes: AskLakesOut | None = None,
    lang: str | None = None,
) -> AskResponse:
    t = result.trace
    zh_reply = replies.reply_lang(result.question, lang) == "zh"
    return AskResponse(
        lakes=lakes,
        state=rag_ask.answer_state(result.question, state),
        question=result.question,
        answer=result.answer,
        answer_source=result.answer_source,
        citations=[
            AskCitationOut(
                id=p.id,
                species_slug=p.species_slug,
                species_name=p.species_name,
                section=p.section,
                title=(p.title_zh or p.title) if zh_reply and p.text_zh else p.title,
                excerpt=p.text_zh if zh_reply and p.text_zh else rag_ask.body_of(p),
                region=p.region,
                sources=[source_out(s) for s in sources_for(p.source_ids)],
                basis=p.basis,
                lang="zh" if zh_reply and p.text_zh else "en",
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
    state, slug = _state(payload), _slug(payload)
    result = rag_ask.search_guides(payload.question, species_slug=slug, state=state, lang=payload.lang)
    ai_can_answer = result.answer_source == rag_ask.ANSWER_PASSAGES or result.trace.outcome in _AI_CAN_ADD_TO
    routed = tuple(result.trace.routed_species or ())
    lakes = lake_facts.answer(db, payload.question, state, routed)
    if lakes is not None and lakes.lakes and (lakes.answers_it or not result.citations):
        # The lake data answers it; a miss for the guides isn't one for Ask.
        result = replace(result, answer="", answer_source=rag_ask.ANSWER_LAKES, citations=[])
        result.trace.outcome = rag_ask.OUTCOME_LAKE
        ai_can_answer = False
    elif lakes is None and (name := lake_facts.missing_lake(payload.question, routed)):
        reply = replies.no_lake(name, replies.reply_lang(payload.question, payload.lang))
        result = replace(result, answer=reply, answer_source=rag_ask.ANSWER_NO_MATCH, citations=[])
        result.trace.outcome = rag_ask.OUTCOME_NO_MATCH
        ai_can_answer = False
    elif lakes is None and lake_facts.asks_where_nearby(payload.question):
        reply = replies.use_the_map(replies.reply_lang(payload.question, payload.lang))
        result = replace(result, answer=reply, answer_source=rag_ask.ANSWER_NO_MATCH, citations=[])
        result.trace.outcome = rag_ask.OUTCOME_NO_MATCH
        ai_can_answer = False
    elif lakes is None and (topic := site_help.topic(payload.question)):
        reply = replies.site_help(topic, replies.reply_lang(payload.question, payload.lang))
        result = replace(result, answer=reply, answer_source=rag_ask.ANSWER_NO_MATCH, citations=[])
        result.trace.outcome = rag_ask.OUTCOME_OK
        ai_can_answer = False
    # What Ask can't answer, without who asked (services/ask_misses.py).
    ask_misses.record(db, payload.question, result.trace.outcome, payload.lang or "en", state, slug)
    out = _response(result, _allowance_out(db, user), state, lakes, payload.lang)
    out.ai_can_answer = ai_can_answer
    return out


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
    the question must be about fishing (a search, no model call), then an
    answer is reserved from today's allowance, then the model is called. An
    answer that doesn't come back model-written (the model was unreachable,
    its answer failed validation and the guides were quoted instead, or it
    read the question as not about fishing) is given back, and so is one
    answered from the cache, which cost nothing.

    Like /advisor/explain, a model failure is not an error: the response is
    still 200, with `answer_source` "fallback" (or "no_match") saying so."""
    slug, state = _slug(payload), _state(payload)
    found = rag_ask.search_guides(payload.question, species_slug=slug, state=state, lang=payload.lang)
    if not found.citations and found.trace.outcome == rag_ask.OUTCOME_OFF_TOPIC:
        raise HTTPException(status_code=422, detail=NOT_A_FISHING_QUESTION)

    if ai_budget.exhausted(db):
        raise HTTPException(status_code=503, detail=ai_budget.PAUSED)

    day = ai_quota.today()
    if not ai_quota.reserve(db, user, day):
        raise HTTPException(
            status_code=429,
            detail=(
                "You've used today's free AI answer. Searching the guides is still free; "
                "the AI answer comes back tomorrow (UTC)."
            ),
        )

    result = rag_ask.ask(payload.question, species_slug=slug, state=state, lang=payload.lang)
    if result.answer_source != rag_ask.ANSWER_LLM or result.trace.cache_hit:
        ai_quota.give_back(db, user, day)
    return _response(result, _allowance_out(db, user), state, lang=payload.lang)
