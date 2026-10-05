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

from app.knowledge.species_guides import GUIDES
from app.services.llm import LLMProvider, LLMUnavailable, get_provider
from app.services.rag.chunking import Passage
from app.services.rag.retriever import Retriever, ScoredPassage, default_retriever, split_species

DEFAULT_K = 4
MAX_ATTEMPTS = 2
MAX_ANSWER_CHARS = 1500
CACHE_TTL_SECONDS = 60 * 60  # the guides only change with a deploy

OUTCOME_OK = "ok"
OUTCOME_NO_MATCH = "no_match"
OUTCOME_INVALID_JSON = "invalid_json"
OUTCOME_UNGROUNDED_CITATION = "ungrounded_citation"
OUTCOME_UNGROUNDED_SPECIES = "ungrounded_species"
OUTCOME_UNGROUNDED_NUMBER = "ungrounded_number"
OUTCOME_URL_IN_ANSWER = "url_in_answer"
OUTCOME_PROVIDER_UNAVAILABLE = "provider_unavailable"

ANSWER_LLM = "llm"
ANSWER_FALLBACK = "fallback"
ANSWER_NO_MATCH = "no_match"

NO_MATCH_ANSWER = (
    "The FishEye fish guides don't cover that yet. They cover twelve Texas freshwater "
    "fish: what each one eats, where and when to find it, which bait and lures work, "
    "and rod-and-reel setups. Try asking about one of those."
)

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
    answer_source: str  # ANSWER_LLM | ANSWER_FALLBACK | ANSWER_NO_MATCH
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


def ask(
    question: str,
    species_slug: str | None = None,
    k: int = DEFAULT_K,
    provider: LLMProvider | None = None,
    retriever: Retriever | None = None,
) -> AskResult:
    """Never raises on model failure — falls back."""
    question = " ".join(question.split())
    retr = retriever or default_retriever()
    context = (species_slug,) if species_slug else None
    hits: list[ScoredPassage] = retr.search(question, k=k, species=context)

    named, _ = split_species(question)
    trace = AskTrace(
        trace_id=str(uuid.uuid4()),
        routed_species=list(named or context or ()),
        retrieved=[{"id": h.passage.id, "score": round(h.score, 3)} for h in hits],
    )
    passages = [h.passage for h in hits]

    if not passages:
        trace.outcome = OUTCOME_NO_MATCH
        return AskResult(question, NO_MATCH_ANSWER, ANSWER_NO_MATCH, [], trace)

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
