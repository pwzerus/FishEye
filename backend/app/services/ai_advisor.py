"""The AI advisor: PRD §5.1's RAG flow, with the model kept on a short leash.

The flow, and where the guardrails sit
--------------------------------------
1. Gather structured facts from things that are *already* authoritative in
   this system: the scored candidates from the rule engine, the lake's
   confirmed species with their evidence sentences and source URLs, and the
   current weather snapshot.
2. Hand those facts to the model with an instruction to explain them.
3. Parse the reply as JSON, validate it against a Pydantic schema, and then
   run two grounding checks the schema alone can't express:
     - every cited URL must be one step 1 supplied;
     - no species may be named that isn't confirmed *in this lake*.
4. On any failure: retry once, then fall back to a fixed template built
   from the same facts. Never show the user raw model text.

Why the grounding checks are the interesting part
-------------------------------------------------
"Only use the provided facts" in a system prompt is a request, not a
guarantee — and the two failures that matter most here are exactly the ones
a prompt can't prevent: inventing a source (which makes a made-up claim
look sourced) and inventing a fish (constraint 1's explicit prohibition:
the LLM must not decide what lives in a lake). Both are mechanically
checkable against data the backend already has, so they're checked, not
hoped for. A response that fails either check is discarded entirely — not
patched up — because a model that fabricated one citation has told you
something about the rest of that answer.

What deliberately never passes through the model
------------------------------------------------
Safety warnings and confidence. See schemas/advisor.py for the reasoning.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.waterbody import Species, Waterbody, WaterbodySpecies
from app.schemas.advisor import AdvisorExplanationOut
from app.services.llm import LLMProvider, LLMUnavailable, get_provider
from app.services.recommendations import WaterbodyNotFound, build_recommendations
from app.services.scoring import downwind_shore
from app.services.weather_adapter import WeatherSnapshot

MAX_ATTEMPTS = 2
CACHE_TTL_SECONDS = 15 * 60

OUTCOME_OK = "ok"
OUTCOME_INVALID_JSON = "invalid_json"
OUTCOME_UNGROUNDED_SOURCE = "ungrounded_source"
OUTCOME_UNGROUNDED_SPECIES = "ungrounded_species"
OUTCOME_PROVIDER_UNAVAILABLE = "provider_unavailable"


class GroundingError(Exception):
    """The model's output referenced something the backend never supplied."""

    def __init__(self, outcome: str, detail: str) -> None:
        super().__init__(detail)
        self.outcome = outcome


@dataclass
class AdvisorTrace:
    """PRD constraint 14. Holds no identity documents and no coordinates
    beyond the public access points already published by the API."""

    trace_id: str
    provider: str = "none"
    model: str = "none"
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    validation_attempts: int = 0
    outcome: str = OUTCOME_OK
    retrieved_source_count: int = 0
    cache_hit: bool = False
    # Kept in-process for debugging; not returned by the API.
    retrieved_sources: list[str] = field(default_factory=list)


@dataclass
class AdvisorResult:
    facts: dict[str, Any]
    explanation: AdvisorExplanationOut
    answer_source: str  # "llm" | "fallback"
    trace: AdvisorTrace


# --------------------------------------------------------------------------
# 1. Fact gathering (the "R" in RAG)
# --------------------------------------------------------------------------


def gather_facts(
    db: Session,
    waterbody_id: int,
    target_species: str | None = None,
    limit: int = 3,
    weather: WeatherSnapshot | None = None,
) -> dict[str, Any]:
    """Everything the model is allowed to know, in one payload.

    This is also the allow-list the grounding checks validate against, which
    is why it's built once and passed around rather than re-queried: the
    facts the model saw and the facts it's checked against must be the same
    set, or the check is theatre.
    """
    waterbody = db.get(Waterbody, waterbody_id)
    if waterbody is None:
        raise WaterbodyNotFound(f"no waterbody with id {waterbody_id}")

    recommendations = build_recommendations(
        db, waterbody_id, target_species=target_species, limit=limit, weather=weather
    )

    species_rows = list(
        db.execute(
            select(WaterbodySpecies, Species)
            .join(Species, WaterbodySpecies.species_id == Species.id)
            .where(WaterbodySpecies.waterbody_id == waterbody_id)
        ).all()
    )

    species_facts = [
        {
            "common_name": species.common_name,
            "confidence": link.confidence,
            "evidence": link.evidence,
            "source_url": link.source_url,
            "observed_at": link.observed_at.isoformat() if link.observed_at else None,
        }
        for link, species in species_rows
    ]

    # Citations the model may use. Anything outside this set is a
    # fabrication by definition.
    # An OSM-tier lake's source is a community map, not an official one, and
    # the citation label is shown to users verbatim.
    source_kind = (
        "OpenStreetMap (community-mapped)" if waterbody.data_tier == "osm" else "official source"
    )
    sources: list[dict[str, str]] = [
        {"url": waterbody.source_url, "label": f"{waterbody.name} — {source_kind}"}
    ]
    for fact in species_facts:
        if fact["source_url"] and all(s["url"] != fact["source_url"] for s in sources):
            sources.append(
                {"url": fact["source_url"], "label": f"{fact['common_name']} evidence"}
            )

    snapshot_source = recommendations["weather_source"]
    current = weather.current if weather else None

    return {
        "waterbody_id": waterbody.id,
        "waterbody_name": waterbody.name,
        "public_access_status": waterbody.public_access_status,
        "target_species": target_species,
        "candidates": recommendations["candidates"],
        "best_time_window": (
            {
                "start_time": recommendations["best_time_window"]["start_time"].isoformat(),
                "end_time": recommendations["best_time_window"]["end_time"].isoformat(),
                "reason": recommendations["best_time_window"]["reason"],
            }
            if recommendations["best_time_window"]
            else None
        ),
        "weather": {
            "source": snapshot_source,
            "wind_direction": current.wind_direction if current else None,
            "wind_speed": current.wind_speed if current else None,
            "downwind_shore": downwind_shore(current.wind_direction) if current else None,
            "short_forecast": current.short_forecast if current else None,
        },
        "species_confirmed_here": species_facts,
        "sources": sources,
        # Server-controlled, included so the model can *mention* them but
        # never so it can decide them — the response carries the backend's
        # own copies regardless of what comes back.
        "safety_warnings": recommendations["safety_warnings"],
        "_recommendations": recommendations,
    }


# --------------------------------------------------------------------------
# 2. Prompting
# --------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a fishing guide explaining a decision that has \
already been made by a rule-based scoring engine.

You must follow these rules exactly:
- Use ONLY the facts inside the <facts> block. You have no other knowledge \
of this lake.
- Never state that a fish species is present unless it appears in \
species_confirmed_here.
- Never cite a URL that is not in the sources list.
- Never invent coordinates, regulations, or access points.
- You are explaining the ranking, not producing it. If a candidate scored \
well, say which factor drove it, using the factor reasons given.
- Write for a beginner: short, concrete, no jargon.

Reply with ONLY a JSON object, no prose around it, in this shape:
{"summary": str, "gear": [str], "bait": [str], "steps": [str], \
"risks": [str], "sources": [str]}
where every entry of "sources" is a URL copied exactly from the facts."""


def build_user_prompt(facts: dict[str, Any]) -> str:
    """Serialize the facts for the model.

    The `_`-prefixed keys are internal plumbing (the full recommendation
    payload we reuse when building the fallback) and are stripped here —
    the model sees exactly the facts it's allowed to use, and nothing about
    how this service is wired together.
    """
    public_facts = {k: v for k, v in facts.items() if not k.startswith("_")}
    return (
        "Explain these fishing recommendations.\n\n"
        f"<facts>\n{json.dumps(public_facts, ensure_ascii=False, default=str)}\n</facts>"
    )


# --------------------------------------------------------------------------
# 3. Validation + grounding
# --------------------------------------------------------------------------

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_and_validate(
    raw_text: str, facts: dict[str, Any], db: Session
) -> AdvisorExplanationOut:
    """Turn raw model text into a validated explanation, or raise.

    Raises GroundingError (with the trace outcome to record) on anything
    unusable. Never returns partial or repaired output.
    """
    match = _JSON_OBJECT_RE.search(raw_text or "")
    if match is None:
        raise GroundingError(OUTCOME_INVALID_JSON, "no JSON object in model output")
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise GroundingError(OUTCOME_INVALID_JSON, f"unparseable JSON: {exc}") from exc

    allowed_sources = {s["url"] for s in facts["sources"]}
    source_labels = {s["url"]: s["label"] for s in facts["sources"]}

    # The model returns bare URL strings; the API returns labelled sources.
    # Doing the expansion here (rather than asking the model for labels)
    # removes one more thing it could get wrong.
    raw_sources = payload.get("sources", [])
    if not isinstance(raw_sources, list):
        raise GroundingError(OUTCOME_INVALID_JSON, "sources is not a list")

    cited: list[dict[str, str]] = []
    for url in raw_sources:
        if not isinstance(url, str):
            raise GroundingError(OUTCOME_INVALID_JSON, "a source entry was not a string")
        if url not in allowed_sources:
            raise GroundingError(
                OUTCOME_UNGROUNDED_SOURCE,
                f"model cited a source that was never supplied: {url!r}",
            )
        cited.append({"url": url, "label": source_labels[url]})
    payload["sources"] = cited

    try:
        explanation = AdvisorExplanationOut.model_validate(payload)
    except ValidationError as exc:
        raise GroundingError(OUTCOME_INVALID_JSON, f"schema validation failed: {exc}") from exc

    _reject_unconfirmed_species(explanation, facts, db)
    return explanation


def _reject_unconfirmed_species(
    explanation: AdvisorExplanationOut, facts: dict[str, Any], db: Session
) -> None:
    """Constraint 1, enforced rather than requested.

    The check is deliberately narrow: it compares the model's prose against
    the species vocabulary this system actually knows about, and rejects any
    that aren't confirmed *for this lake*. It cannot catch every possible
    fabrication — no static check can — but it catches the specific one the
    PRD singles out, which is the one that would put a fish in a lake on a
    user's say-so from a language model.

    Known limitation: this relies on species names being distinctive enough
    not to collide with ordinary fishing prose. Every name in the current
    vocabulary is multi-word ("White Bass", "Channel Catfish"), so "bring a
    bass rod" can't trip it. Adding a bare single-word species ("Bass",
    "Crappie") would start rejecting good answers over gear talk — the
    failure would be loud (everything falls back) rather than silent, but
    it's a real constraint on what may be added to the Species table, not a
    theoretical one.
    """
    confirmed = {s["common_name"].lower() for s in facts["species_confirmed_here"]}
    known = {
        name.lower()
        for (name,) in db.execute(select(Species.common_name)).all()
    }
    unconfirmed_vocabulary = known - confirmed
    if not unconfirmed_vocabulary:
        return

    prose = " ".join(
        [
            explanation.summary,
            *explanation.gear,
            *explanation.bait,
            *explanation.steps,
            *explanation.risks,
        ]
    ).lower()

    for species_name in sorted(unconfirmed_vocabulary):
        if re.search(rf"\b{re.escape(species_name)}\b", prose):
            raise GroundingError(
                OUTCOME_UNGROUNDED_SPECIES,
                f"model named {species_name!r}, which is not confirmed in this lake",
            )


# --------------------------------------------------------------------------
# 4. Fallback
# --------------------------------------------------------------------------


def fixed_template_explanation(facts: dict[str, Any]) -> AdvisorExplanationOut:
    """What the user gets when the model can't be trusted or reached.

    Built from the same facts, so it is never *wrong* — only plainer. It
    says so explicitly rather than impersonating a written explanation,
    because a user deciding whether to drive an hour to a lake deserves to
    know how much thought went into what they're reading.
    """
    candidates = facts.get("candidates", [])
    lake = facts["waterbody_name"]
    sources = [
        {"url": s["url"], "label": s["label"]} for s in facts.get("sources", [])
    ]

    if not candidates:
        summary = (
            f"No confirmed-public access points are on file for {lake} yet, so there "
            "is nothing to rank. This is the plain summary — the written explanation "
            "was unavailable."
        )
        steps: list[str] = []
    else:
        top = candidates[0]
        summary = (
            f"Top-ranked spot on {lake}: {top['name']} "
            f"(score {round(top['score'] * 100)}). This is the plain summary — "
            "the written explanation was unavailable, so these are the scoring "
            "engine's own figures."
        )
        steps = [
            f"{c['name']} — {c['access_type'].replace('_', ' ')}, "
            f"score {round(c['score'] * 100)}, confidence {round(c['confidence'] * 100)}%"
            for c in candidates
        ]

    risks: list[str] = []
    if facts.get("weather", {}).get("source") == "fallback":
        risks.append("Live weather was unavailable; conditions are not reflected here.")

    return AdvisorExplanationOut(
        summary=summary,
        gear=[],
        bait=[],
        steps=steps,
        # Pydantic coerces these dicts into AdvisorSourceOut.
        sources=sources,  # type: ignore[arg-type]
        risks=risks,
    )


# --------------------------------------------------------------------------
# 5. Orchestration + cache
# --------------------------------------------------------------------------

_cache: dict[str, tuple[float, AdvisorResult]] = {}
_cache_lock = threading.Lock()


def _cache_key(facts: dict[str, Any]) -> str:
    """Hash the facts themselves.

    Keying on the facts rather than on (lake, species) means the cache
    invalidates itself the moment anything the answer depends on changes —
    new weather, a re-scored candidate, a newly ingested species record —
    without this module having to know which of those moved.
    """
    public_facts = {k: v for k, v in facts.items() if not k.startswith("_")}
    blob = json.dumps(public_facts, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def reset_cache() -> None:
    with _cache_lock:
        _cache.clear()


def explain(
    db: Session,
    waterbody_id: int,
    target_species: str | None = None,
    limit: int = 3,
    weather: WeatherSnapshot | None = None,
    provider: LLMProvider | None = None,
) -> AdvisorResult:
    """Run the full flow. Never raises on model failure — falls back."""
    facts = gather_facts(
        db, waterbody_id, target_species=target_species, limit=limit, weather=weather
    )
    trace = AdvisorTrace(
        trace_id=str(uuid.uuid4()),
        retrieved_source_count=len(facts["sources"]),
        retrieved_sources=[s["url"] for s in facts["sources"]],
    )

    key = _cache_key(facts)
    with _cache_lock:
        entry = _cache.get(key)
        if entry is not None and time.time() - entry[0] < CACHE_TTL_SECONDS:
            cached = entry[1]
            hit_trace = AdvisorTrace(**{**vars(cached.trace), "trace_id": trace.trace_id})
            hit_trace.cache_hit = True
            return AdvisorResult(
                facts=facts,
                explanation=cached.explanation,
                answer_source=cached.answer_source,
                trace=hit_trace,
            )

    llm = provider or get_provider()
    system_prompt = SYSTEM_PROMPT
    user_prompt = build_user_prompt(facts)

    last_outcome = OUTCOME_OK
    for attempt in range(1, MAX_ATTEMPTS + 1):
        trace.validation_attempts = attempt
        try:
            response = llm.complete(system_prompt, user_prompt)
        except LLMUnavailable:
            # An outage isn't retried here: the provider is responsible for
            # its own timeout/retry envelope, and a second immediate call
            # to a provider that just declared itself down only adds latency
            # to a user's failed request.
            trace.provider = getattr(llm, "name", "unknown")
            trace.outcome = OUTCOME_PROVIDER_UNAVAILABLE
            trace.validation_attempts = attempt - 1
            return _fallback_result(facts, trace)

        trace.provider = response.provider
        trace.model = response.model
        trace.latency_ms += response.latency_ms
        trace.prompt_tokens += response.prompt_tokens
        trace.completion_tokens += response.completion_tokens
        trace.estimated_cost_usd += response.estimated_cost_usd

        try:
            explanation = parse_and_validate(response.text, facts, db)
        except GroundingError as exc:
            last_outcome = exc.outcome
            continue

        trace.outcome = OUTCOME_OK
        result = AdvisorResult(
            facts=facts, explanation=explanation, answer_source="llm", trace=trace
        )
        with _cache_lock:
            _cache[key] = (time.time(), result)
        return result

    trace.outcome = last_outcome
    return _fallback_result(facts, trace)


def _fallback_result(facts: dict[str, Any], trace: AdvisorTrace) -> AdvisorResult:
    """Fallbacks are deliberately NOT cached: the next request should get a
    fresh attempt at a real answer rather than being served a degraded one
    for the next 15 minutes because of a single bad moment."""
    return AdvisorResult(
        facts=facts,
        explanation=fixed_template_explanation(facts),
        answer_source="fallback",
        trace=trace,
    )


def server_controlled_fields(facts: dict[str, Any]) -> dict[str, Any]:
    """The parts of the response the model never touches (see
    schemas/advisor.py). Confidence is the top candidate's, from the scoring
    engine — the share of the intended signal that actually had data."""
    recommendations = facts["_recommendations"]
    candidates = recommendations["candidates"]
    return {
        "confidence": candidates[0]["confidence"] if candidates else 0.0,
        "safety_warnings": recommendations["safety_warnings"],
        "best_time_window": recommendations["best_time_window"],
        "candidates": candidates,
        "weather_source": recommendations["weather_source"],
        "generated_at": datetime.now(timezone.utc),
    }
