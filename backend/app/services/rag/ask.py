"""Answer a beginner's question from the reviewed fish guides, with citations.

Same leash as ai_advisor.py, applied to open-ended questions
------------------------------------------------------------
1. Retrieve up to K passages (retriever.py). If nothing matches, say the
   guides don't cover it — the model is never called with nothing to go on,
   because "answer from these passages" with zero passages is an invitation
   to answer from memory.
2. Ask the model to answer only from those passages and to cite them by id.
3. Validate before anything reaches the user:
     - the reply is JSON of the expected shape;
     - every citation is a passage it was actually given;
     - no URL in the prose (sources are attached by the server, from the
       citations — the model never writes a link);
     - every fish the answer names appears in the passages it was given;
     - every number in the answer appears in those passages (or in the
       question). The guides' own rule is "no invented numbers" — hook
       sizes and line weights are exactly what a model fills in from
       memory, and exactly what a beginner copies to the tackle shop.
4. Any failure: retry once, then fall back to quoting the top passages
   verbatim. The fallback can't be wrong about the guides, only plainer,
   and it says so.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.knowledge import jurisdictions
from app.knowledge.species_guides import GUIDES
from app.services.llm import LLMProvider, LLMUnavailable, get_provider
from app.services.rag import regional
from app.services.rag.chunking import Passage
from app.services.rag.retriever import (
    EMPTY_NOT_COVERED,
    EMPTY_OFF_TOPIC,
    EMPTY_UNGUIDED_FISH,
    Retriever,
    ScoredPassage,
    default_retriever,
    split_species,
    unguided_fish_named,
)
from app.services.rag import es, ja, ko, replies

DEFAULT_K = 4
MAX_ATTEMPTS = 2
MAX_ANSWER_CHARS = 1500
CACHE_TTL_SECONDS = 60 * 60  # the guides only change with a deploy

OUTCOME_OK = "ok"
OUTCOME_NO_MATCH = "no_match"
# Why nothing was retrieved (retriever.EMPTY_*, docs/adr/0026). The trace
# says which, so the reason the person is given is the one the retriever had.
OUTCOME_OFF_TOPIC = "off_topic"
OUTCOME_UNGUIDED_FISH = "unguided_fish"
# The only passages that answer are another state's rules (docs/adr/0027).
OUTCOME_OTHER_STATE = "other_state"
OUTCOME_INVALID_JSON = "invalid_json"
OUTCOME_UNGROUNDED_CITATION = "ungrounded_citation"
OUTCOME_UNGROUNDED_SPECIES = "ungrounded_species"
OUTCOME_UNGROUNDED_NUMBER = "ungrounded_number"
OUTCOME_URL_IN_ANSWER = "url_in_answer"
OUTCOME_PROVIDER_UNAVAILABLE = "provider_unavailable"

ANSWER_LLM = "llm"
ANSWER_FALLBACK = "fallback"
ANSWER_NO_MATCH = "no_match"
# The passages themselves, no model involved: what everyone gets first
# (search_guides below). A written answer is a separate, metered step.
ANSWER_PASSAGES = "passages"
PASSAGES_INTRO = "Here's what the FishEye guides say:"
# The passages are in English; a question in Chinese is told so in Chinese.
PASSAGES_INTRO_ZH = "以下是 FishEye 指南里的相关内容（原文为英文）："

# Three different admissions, because they are three different situations
# and one "not covered" for all of them was misleading (docs/adr/0026). In
# the asker's language: replies.py.
COVERAGE = replies.coverage("en")
NO_MATCH_ANSWER = replies.no_match("en")
OFF_TOPIC_ANSWER = replies.off_topic("en")


def unguided_fish_answer(name: str) -> str:
    return replies.unguided_fish(name, "en")


def searchable(question: str) -> str:
    """The question in the words the search is decided by: a Japanese,
    Korean or Spanish one in English (ja.py, ko.py, es.py); any other as it
    is. Japanese first: its kanji would otherwise read as Chinese."""
    if ja.is_japanese(question):
        return ja.to_english(question)
    if ko.is_korean(question):
        return ko.to_english(question)
    return es.to_english(question) if es.is_spanish(question) else question

SPECIES_VOCABULARY = tuple(sorted((g.common_name.lower() for g in GUIDES), key=len, reverse=True))


class GroundingError(Exception):
    def __init__(self, outcome: str, detail: str) -> None:
        super().__init__(detail)
        self.outcome = outcome


@dataclass
class AskTrace:
    trace_id: str
    retriever: str = "bm25"
    routed_species: list[str] = field(default_factory=list)
    retrieved: list[dict[str, Any]] = field(default_factory=list)  # [{"id", "score"}]
    provider: str = "none"
    model: str = "none"
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    validation_attempts: int = 0
    outcome: str = OUTCOME_OK
    cache_hit: bool = False


@dataclass
class AskResult:
    question: str
    answer: str
    answer_source: str  # ANSWER_LLM | ANSWER_FALLBACK | ANSWER_NO_MATCH | ANSWER_PASSAGES
    citations: list[Passage]
    trace: AskTrace


# --------------------------------------------------------------------------
# Prompt
# --------------------------------------------------------------------------

SYSTEM_PROMPT = """You answer questions from beginner anglers using ONLY the \
passages you are given, which come from FishEye's reviewed fish guides.

Rules:
- Use only facts stated in the passages. If they don't answer the question, \
say so plainly in one sentence; do not fill the gap from your own knowledge.
- Never write a number (hook size, weight, depth, temperature, length) that \
is not in the passages.
- Never name a fish species that is not in the passages.
- Never write a URL. Cite passages by id instead; the app attaches the links.
- Never state size or bag limits or other regulations beyond what a passage \
says.
- Write for a first-time angler: short, concrete, friendly, 2-5 sentences.

Reply with ONLY a JSON object, no prose around it:
{"answer": str, "citations": [passage id, ...]}
Cite every passage your answer uses, and at least one."""


def build_user_prompt(question: str, passages: list[Passage]) -> str:
    payload = [{"id": p.id, "text": p.text} for p in passages]
    return (
        f"<question>{question}</question>\n\n"
        f"<passages>\n{json.dumps(payload, ensure_ascii=False)}\n</passages>"
    )


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
_URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
_NUMBER_RE = re.compile(r"\d+(?:[./]\d+)?")
_UNICODE_FRACTIONS = {"¼": "1/4", "½": "1/2", "¾": "3/4", "⅛": "1/8", "⅜": "3/8", "⅝": "5/8"}


def _normalize_numbers(text: str) -> str:
    for glyph, ascii_ in _UNICODE_FRACTIONS.items():
        # "1½" -> "1 1/2", so both the whole and the fraction are findable.
        text = re.sub(rf"(\d){glyph}", rf"\1 {ascii_}", text)
        text = text.replace(glyph, ascii_)
    return text


def numbers_in(text: str) -> set[str]:
    return set(_NUMBER_RE.findall(_normalize_numbers(text)))


def species_named(text: str) -> set[str]:
    """Guide species named in `text`, longest names first so "hybrid
    striped bass" isn't also counted as a bare "striped bass"."""
    remaining = text.lower()
    found: set[str] = set()
    for name in SPECIES_VOCABULARY:
        pattern = rf"\b{re.escape(name)}\b"
        if re.search(pattern, remaining):
            found.add(name)
            remaining = re.sub(pattern, " ", remaining)
    return found


def parse_and_validate(
    raw_text: str, question: str, passages: list[Passage]
) -> tuple[str, list[Passage]]:
    """(answer, cited passages) or GroundingError. Never repairs output."""
    match = _JSON_OBJECT_RE.search(raw_text or "")
    if match is None:
        raise GroundingError(OUTCOME_INVALID_JSON, "no JSON object in model output")
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise GroundingError(OUTCOME_INVALID_JSON, f"unparseable JSON: {exc}") from exc

    answer = payload.get("answer") if isinstance(payload, dict) else None
    citations = payload.get("citations") if isinstance(payload, dict) else None
    if not isinstance(answer, str) or not answer.strip():
        raise GroundingError(OUTCOME_INVALID_JSON, "answer missing or empty")
    if len(answer) > MAX_ANSWER_CHARS:
        raise GroundingError(OUTCOME_INVALID_JSON, "answer too long")
    if not isinstance(citations, list) or not citations or not all(
        isinstance(c, str) for c in citations
    ):
        raise GroundingError(OUTCOME_INVALID_JSON, "citations must be a non-empty list of ids")

    by_id = {p.id: p for p in passages}
    cited: list[Passage] = []
    for cid in citations:
        if cid not in by_id:
            raise GroundingError(OUTCOME_UNGROUNDED_CITATION, f"cited unknown passage {cid!r}")
        if by_id[cid] not in cited:
            cited.append(by_id[cid])

    if _URL_RE.search(answer):
        raise GroundingError(OUTCOME_URL_IN_ANSWER, "answer contains a URL")

    # Checked against every passage the model was given, not only the cited
    # ones: a model that uses a passage and forgets to cite it has made a
    # citation slip, not a fabrication. Citations are still required above.
    given_text = " ".join(p.text for p in passages).lower()
    for name in species_named(answer):
        if not re.search(rf"\b{re.escape(name)}\b", given_text):
            raise GroundingError(
                OUTCOME_UNGROUNDED_SPECIES, f"answer names {name!r}, which no passage mentions"
            )

    allowed_numbers = numbers_in(given_text) | numbers_in(question)
    invented = numbers_in(answer) - allowed_numbers
    if invented:
        raise GroundingError(
            OUTCOME_UNGROUNDED_NUMBER, f"answer uses numbers no passage gives: {sorted(invented)}"
        )

    return answer.strip(), cited


# --------------------------------------------------------------------------
# Fallback
# --------------------------------------------------------------------------


def body_of(passage: Passage) -> str:
    """The passage without its "Species — Section:" retrieval header."""
    _, sep, body = passage.text.partition(": ")
    return body if sep else passage.text


def fallback_answer(passages: list[Passage], limit: int = 2) -> tuple[str, list[Passage]]:
    used = passages[:limit]
    parts = [f"{p.species_name or 'All fish'}, {p.title.lower()}: {body_of(p)}" for p in used]
    return "Here's what the FishEye guides say:\n\n" + "\n\n".join(parts), used


# --------------------------------------------------------------------------
# Orchestration + cache
# --------------------------------------------------------------------------

_cache: dict[str, tuple[float, AskResult]] = {}
_cache_lock = threading.Lock()


def reset_cache() -> None:
    with _cache_lock:
        _cache.clear()


def _cache_key(question: str, passages: list[Passage]) -> str:
    # Keyed on the passages too: two phrasings that retrieve the same
    # passages are different questions, but a changed guide invalidates.
    blob = json.dumps(
        [" ".join(question.lower().split()), [(p.id, p.text) for p in passages]]
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _search(
    retr: Retriever, question: str, k: int, context: tuple[str, ...] | None, state: str | None
) -> tuple[list[ScoredPassage], bool]:
    """Retrieval for someone in `state` (docs/adr/0027, 0028): searched in
    that state's own index, which has no other state's rules in it.

    The full index is searched as well, for one decision: if its best match
    is another state's rule, the question is about a rule, and it is
    answered only if this state's own version of that rule turned up.
    Otherwise nothing is shown, because what ranks below is filler, and
    filler under a rules question reads as an answer. The flag says the
    full index had other states' passages, which is what tells "nothing in
    the guides" from "only another state's rules"."""
    if state is None:
        return retr.search(question, k=k, species=context), False
    full = retr.search(question, k=k, species=context)
    foreign = any(not jurisdictions.applies(h.passage.region, state) for h in full)
    view = regional.for_state(retr, state)
    if view is None:  # a retriever regional.py can't restrict: filter instead
        local = [h for h in retr.search(question, k=k + 4, species=context)
                 if jurisdictions.applies(h.passage.region, state)][:k]
    else:
        local = view.search(question, k=k, species=context)
    if full and not jurisdictions.applies(full[0].passage.region, state):
        if not any(h.passage.region == state for h in local):
            return [], True
    if local:
        local = _with_required_bait_rules(retr, local, question, state, k)
    return local, foreign and not local


_BAIT_QUESTION_RE = re.compile(
    r"\b(bait|baits|baitfish|minnows?|shiners?|shad|chum|live\s+fish)\b|饵|小鱼|活鱼", re.I
)


def _with_required_bait_rules(
    retr: Retriever, hits: list[ScoredPassage], question: str, state: str, k: int
) -> list[ScoredPassage]:
    """A bait question in a state whose bait rules contradict the guides'
    advice (California) always shows those rules, in second place: the top
    hit stays the best match, and the rule sits right under it rather than
    being ranked out of view by passages that recommend live minnows."""
    j = jurisdictions.get(state)
    if not (j and j.bait_rules_on_every_bait_question and _BAIT_QUESTION_RE.search(question)):
        return hits
    pid = f"all-fish#{jurisdictions.bait_rules_section(state)}"
    if any(h.passage.id == pid for h in hits):
        return hits
    passage = next((p for p in getattr(retr, "passages", []) if p.id == pid), None)
    if passage is None:
        return hits
    rule = ScoredPassage(passage, hits[0].score if hits else 0.0)
    return (hits[:1] + [rule] + hits[1:])[:k]


def search_guides(
    question: str,
    species_slug: str | None = None,
    k: int = DEFAULT_K,
    retriever: Retriever | None = None,
    state: str | None = None,
    lang: str | None = None,
) -> AskResult:
    """The retrieval half of `ask`, on its own: the passages that answer the
    question, best first, and no model call. An empty result is the same
    "not covered" answer `ask` gives, and is also what decides that a
    question isn't a fishing question and may not spend an AI summary
    (api/ask.py). `lang` is the site's language: FishEye's own sentences
    come back in it, or in the question's (replies.py)."""
    question = " ".join(question.split())
    query = searchable(question)
    reply = replies.reply_lang(question, lang)
    retr = retriever or default_retriever()
    context = (species_slug,) if species_slug else None
    state = answer_state(query, state)
    hits, dropped = _search(retr, query, k, context, state)
    named, _ = split_species(query)
    trace = AskTrace(
        trace_id=str(uuid.uuid4()),
        retriever=getattr(retr, "name", "bm25"),
        routed_species=list(named or context or ()),
        retrieved=[{"id": h.passage.id, "score": round(h.score, 3)} for h in hits],
    )
    if not hits:
        return _empty(question, context, retr, trace, state if dropped else None, query=query, lang=reply)
    passages = [h.passage for h in hits]
    return AskResult(question, replies.passages_intro(reply), ANSWER_PASSAGES, passages, trace)


def answer_state(question: str, picked: str | None) -> str | None:
    """Whose rules to answer with: a state the question names wins over the
    one picked on the page ("license in Minnesota" from a Texan is about
    Minnesota), then the picked one, else None (every state's, labelled)."""
    return jurisdictions.state_in_question(question) or jurisdictions.normalize(picked)


def _empty(
    question: str,
    context: tuple[str, ...] | None,
    retr: Retriever,
    trace: AskTrace,
    other_state: str | None = None,
    query: str | None = None,
    lang: str | None = None,
) -> AskResult:
    """The answer when nothing was retrieved: which of the kinds depends on
    why the retriever came back empty (docs/adr/0026), or on every hit
    having been another state's rules (docs/adr/0027). `query` is what was
    searched (a Spanish question's English words); `lang` the reply's."""
    query = query or question
    lang = lang or replies.reply_lang(question, None)
    if other_state:
        trace.outcome = OUTCOME_OTHER_STATE
        return AskResult(question, replies.other_state(other_state, lang), ANSWER_NO_MATCH, [], trace)
    why = retr.why_empty(query, context) if hasattr(retr, "why_empty") else EMPTY_NOT_COVERED
    if why == EMPTY_OFF_TOPIC:
        trace.outcome = OUTCOME_OFF_TOPIC
        answer = replies.off_topic(lang)
    elif why == EMPTY_UNGUIDED_FISH:
        trace.outcome = OUTCOME_UNGUIDED_FISH
        answer = replies.unguided_fish(unguided_fish_named(query) or replies.THAT_FISH.get(lang, "that fish"), lang)
    else:
        trace.outcome = OUTCOME_NO_MATCH
        answer = replies.no_match(lang)
    return AskResult(question, answer, ANSWER_NO_MATCH, [], trace)


def ask(
    question: str,
    species_slug: str | None = None,
    k: int = DEFAULT_K,
    provider: LLMProvider | None = None,
    retriever: Retriever | None = None,
    state: str | None = None,
    lang: str | None = None,
) -> AskResult:
    """Never raises on model failure — falls back. The model sees the
    question as asked, so it answers in its language; the search sees
    `searchable(question)`."""
    question = " ".join(question.split())
    query = searchable(question)
    retr = retriever or default_retriever()
    context = (species_slug,) if species_slug else None
    state = answer_state(query, state)
    hits, dropped = _search(retr, query, k, context, state)

    named, _ = split_species(query)
    trace = AskTrace(
        trace_id=str(uuid.uuid4()),
        retriever=getattr(retr, "name", "bm25"),
        routed_species=list(named or context or ()),
        retrieved=[{"id": h.passage.id, "score": round(h.score, 3)} for h in hits],
    )
    passages = [h.passage for h in hits]

    if not passages:
        return _empty(
            question, context, retr, trace, state if dropped else None,
            query=query, lang=replies.reply_lang(question, lang),
        )

    key = _cache_key(question, passages)
    with _cache_lock:
        entry = _cache.get(key)
        if entry is not None and time.time() - entry[0] < CACHE_TTL_SECONDS:
            cached = entry[1]
            hit = AskTrace(**{**vars(cached.trace), "trace_id": trace.trace_id, "cache_hit": True})
            return AskResult(question, cached.answer, cached.answer_source, cached.citations, hit)

    llm = provider or get_provider()
    user_prompt = build_user_prompt(question, passages)
    last_outcome = OUTCOME_OK

    for attempt in range(1, MAX_ATTEMPTS + 1):
        trace.validation_attempts = attempt
        try:
            response = llm.complete(SYSTEM_PROMPT, user_prompt)
        except LLMUnavailable:
            trace.provider = getattr(llm, "name", "unknown")
            trace.outcome = OUTCOME_PROVIDER_UNAVAILABLE
            trace.validation_attempts = attempt - 1
            return _fallback(question, passages, trace)

        trace.provider = response.provider
        trace.model = response.model
        trace.latency_ms += response.latency_ms
        trace.prompt_tokens += response.prompt_tokens
        trace.completion_tokens += response.completion_tokens
        trace.estimated_cost_usd += response.estimated_cost_usd

        try:
            answer, cited = parse_and_validate(response.text, question, passages)
        except GroundingError as exc:
            last_outcome = exc.outcome
            continue

        trace.outcome = OUTCOME_OK
        result = AskResult(question, answer, ANSWER_LLM, cited, trace)
        with _cache_lock:
            _cache[key] = (time.time(), result)
        return result

    trace.outcome = last_outcome
    return _fallback(question, passages, trace)


def _fallback(question: str, passages: list[Passage], trace: AskTrace) -> AskResult:
    """Not cached, for the same reason as ai_advisor's fallback: one bad
    moment shouldn't pin a degraded answer for the next hour."""
    answer, used = fallback_answer(passages)
    return AskResult(question, answer, ANSWER_FALLBACK, used, trace)
