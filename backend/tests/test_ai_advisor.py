"""Tests for the AI advisor. Network-free: the mock provider is the point,
not a stand-in for one (see services/llm/mock.py).

The tests worth reading here are the grounding ones — a fabricated citation
and a fabricated species are the two failures PRD constraint 1 exists to
prevent, and they're the reason the validation layer is not just
`json.loads` plus a Pydantic model.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from app.models.waterbody import AccessPoint, Species
from app.schemas.advisor import AdvisorExplanationOut
from app.services import ai_advisor
from app.services import recommendations as rec_module
from app.services.ai_advisor import (
    OUTCOME_INVALID_JSON,
    OUTCOME_OK,
    OUTCOME_PROVIDER_UNAVAILABLE,
    OUTCOME_UNGROUNDED_SOURCE,
    OUTCOME_UNGROUNDED_SPECIES,
    GroundingError,
)
from app.services.llm import MockProvider
from app.services.llm.base import LLMProvider, LLMResponse, LLMUnavailable
from app.services.llm.mock import (
    FAILURE_HALLUCINATED_SOURCE,
    FAILURE_HALLUCINATED_SPECIES,
    FAILURE_INVALID_JSON,
    FAILURE_UNAVAILABLE,
)
from app.services.weather_adapter import (
    CurrentConditions,
    HourlyPeriod,
    WeatherAlert,
    WeatherSnapshot,
)

NOW = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)


def _snapshot(*, source: str = "nws", alerts: list[WeatherAlert] | None = None) -> WeatherSnapshot:
    return WeatherSnapshot(
        latitude=32.8,
        longitude=-95.6,
        current=CurrentConditions(
            temperature=72,
            temperature_unit="F",
            wind_speed="10 mph",
            wind_direction="SE",
            short_forecast="Partly Sunny",
            is_daytime=True,
        ),
        hourly=[]
        if source == "fallback"
        else [
            HourlyPeriod(
                start_time=NOW,
                temperature=72,
                temperature_unit="F",
                wind_speed="10 mph",
                wind_direction="SE",
                short_forecast="Partly Sunny",
                probability_of_precipitation=10,
            )
        ],
        alerts=alerts or [],
        source=source,
        stale=source == "fallback",
        fetched_at=NOW,
    )


@pytest.fixture(autouse=True)
def _clear_cache():
    ai_advisor.reset_cache()
    yield
    ai_advisor.reset_cache()


class _ScriptedProvider(LLMProvider):
    """Returns exactly what a test tells it to, so validation can be
    exercised against output no sane mock would produce."""

    name = "scripted"

    def __init__(self, *texts: str) -> None:
        self.texts = list(texts)
        self.calls = 0

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        self.calls += 1
        text = self.texts[min(self.calls - 1, len(self.texts) - 1)]
        return LLMResponse(
            text=text,
            provider=self.name,
            model="scripted-v1",
            prompt_tokens=10,
            completion_tokens=5,
            estimated_cost_usd=0.0001,
            latency_ms=1.0,
        )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_mock_provider_produces_a_valid_grounded_explanation(db_session, seeded_lake):
    result = ai_advisor.explain(
        db_session,
        waterbody_id=seeded_lake["waterbody"].id,
        target_species="Largemouth Bass",
        weather=_snapshot(),
        provider=MockProvider(),
    )

    assert result.answer_source == "llm"
    assert result.trace.outcome == OUTCOME_OK
    assert result.trace.provider == "mock"
    assert "Lake Fork Dam Bank Access" in result.explanation.summary
    # Every citation came from the backend's own source list.
    allowed = {s["url"] for s in result.facts["sources"]}
    assert {s.url for s in result.explanation.sources} <= allowed


def test_explanation_relays_the_scoring_engines_own_reason(db_session, seeded_lake):
    result = ai_advisor.explain(
        db_session,
        waterbody_id=seeded_lake["waterbody"].id,
        weather=_snapshot(),
        provider=MockProvider(),
    )
    # The mock quotes a factor reason verbatim rather than inventing one:
    # constraint 3 says the LLM explains the ranking, it doesn't produce it.
    top = result.facts["candidates"][0]
    reasons = [f["reason"] for f in top["factors"] if f["value"] is not None]
    assert any(reason in result.explanation.summary for reason in reasons)


# ---------------------------------------------------------------------------
# Grounding: the checks that make "only use these facts" a guarantee
# ---------------------------------------------------------------------------


def test_a_fabricated_citation_is_rejected_and_falls_back(db_session, seeded_lake):
    result = ai_advisor.explain(
        db_session,
        waterbody_id=seeded_lake["waterbody"].id,
        weather=_snapshot(),
        provider=MockProvider(failure_mode=FAILURE_HALLUCINATED_SOURCE),
    )

    assert result.answer_source == "fallback"
    assert result.trace.outcome == OUTCOME_UNGROUNDED_SOURCE
    # The whole answer is discarded, not just the bad citation — a model
    # that invented one source has said something about the rest of it.
    assert "made-up-fishing-blog" not in json.dumps(result.explanation.model_dump())


def test_naming_a_species_not_confirmed_in_this_lake_is_rejected(db_session, seeded_lake):
    # Peacock Bass exists in the system's vocabulary but not in this lake,
    # which is exactly the case constraint 1 prohibits an LLM from deciding.
    db_session.add(
        Species(
            common_name="Peacock Bass",
            scientific_name="Cichla ocellaris",
            difficulty="advanced",
            profile="not present in Texas",
        )
    )
    db_session.commit()

    result = ai_advisor.explain(
        db_session,
        waterbody_id=seeded_lake["waterbody"].id,
        weather=_snapshot(),
        provider=MockProvider(failure_mode=FAILURE_HALLUCINATED_SPECIES),
    )

    assert result.answer_source == "fallback"
    assert result.trace.outcome == OUTCOME_UNGROUNDED_SPECIES
    assert "Peacock Bass" not in result.explanation.summary


def test_a_species_that_is_confirmed_here_is_allowed(db_session, seeded_lake):
    facts = ai_advisor.gather_facts(
        db_session, seeded_lake["waterbody"].id, weather=_snapshot()
    )
    explanation = AdvisorExplanationOut(
        summary="Largemouth Bass are confirmed here by the lake's own survey.",
    )
    # Must not raise: the species is in species_confirmed_here.
    ai_advisor._reject_unconfirmed_species(explanation, facts, db_session)


def test_generic_gear_talk_does_not_trip_the_species_check(db_session, seeded_lake):
    """The check must not fire on ordinary fishing vocabulary, or every good
    answer gets discarded and users only ever see the fallback — a guardrail
    that cries wolf is worse than none.

    This works because every species name in the vocabulary is multi-word
    ("White Bass", "Channel Catfish"), so generic words like "bass" can't
    match one. See the note in _reject_unconfirmed_species about what a
    single-word vocabulary entry would do.
    """
    db_session.add(
        Species(
            common_name="White Bass",
            scientific_name="Morone chrysops",
            difficulty="intermediate",
            profile="not confirmed in this lake",
        )
    )
    db_session.commit()
    facts = ai_advisor.gather_facts(
        db_session, seeded_lake["waterbody"].id, weather=_snapshot()
    )

    # Generic bass talk, and a *confirmed* species, both fine.
    ai_advisor._reject_unconfirmed_species(
        AdvisorExplanationOut(
            summary="Bring a bass-action rod; Largemouth Bass are confirmed here."
        ),
        facts,
        db_session,
    )

    # Naming the unconfirmed species itself is not.
    with pytest.raises(GroundingError):
        ai_advisor._reject_unconfirmed_species(
            AdvisorExplanationOut(summary="White Bass are schooling off the point."),
            facts,
            db_session,
        )


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------


def test_invalid_json_is_retried_once_then_falls_back(db_session, seeded_lake):
    provider = _ScriptedProvider("not json at all", "still not json")
    result = ai_advisor.explain(
        db_session,
        waterbody_id=seeded_lake["waterbody"].id,
        weather=_snapshot(),
        provider=provider,
    )

    assert provider.calls == ai_advisor.MAX_ATTEMPTS
    assert result.answer_source == "fallback"
    assert result.trace.outcome == OUTCOME_INVALID_JSON
    assert result.trace.validation_attempts == ai_advisor.MAX_ATTEMPTS


def test_a_second_attempt_can_succeed(db_session, seeded_lake):
    good = json.dumps(
        {
            "summary": "A plain, grounded summary.",
            "gear": [],
            "bait": [],
            "steps": [],
            "risks": [],
            "sources": [],
        }
    )
    provider = _ScriptedProvider("garbage", good)
    result = ai_advisor.explain(
        db_session,
        waterbody_id=seeded_lake["waterbody"].id,
        weather=_snapshot(),
        provider=provider,
    )

    assert result.answer_source == "llm"
    assert result.trace.validation_attempts == 2
    # Both attempts' tokens are counted — the retry wasn't free.
    assert result.trace.prompt_tokens == 20


def test_provider_outage_falls_back_without_retrying(db_session, seeded_lake):
    class _Down(LLMProvider):
        name = "down"

        def __init__(self) -> None:
            self.calls = 0

        def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
            self.calls += 1
            raise LLMUnavailable("simulated outage")

    provider = _Down()
    result = ai_advisor.explain(
        db_session,
        waterbody_id=seeded_lake["waterbody"].id,
        weather=_snapshot(),
        provider=provider,
    )

    assert provider.calls == 1  # an outage is not retried in this layer
    assert result.answer_source == "fallback"
    assert result.trace.outcome == OUTCOME_PROVIDER_UNAVAILABLE


def test_mock_failure_mode_unavailable_is_demoable(db_session, seeded_lake):
    result = ai_advisor.explain(
        db_session,
        waterbody_id=seeded_lake["waterbody"].id,
        weather=_snapshot(),
        provider=MockProvider(failure_mode=FAILURE_UNAVAILABLE),
    )
    assert result.answer_source == "fallback"
    assert result.trace.outcome == OUTCOME_PROVIDER_UNAVAILABLE


def test_mock_failure_mode_invalid_json_is_demoable(db_session, seeded_lake):
    result = ai_advisor.explain(
        db_session,
        waterbody_id=seeded_lake["waterbody"].id,
        weather=_snapshot(),
        provider=MockProvider(failure_mode=FAILURE_INVALID_JSON),
    )
    assert result.answer_source == "fallback"
    assert result.trace.outcome == OUTCOME_INVALID_JSON


def test_fallback_explanation_states_that_it_is_the_plain_version(db_session, seeded_lake):
    facts = ai_advisor.gather_facts(
        db_session, seeded_lake["waterbody"].id, weather=_snapshot()
    )
    explanation = ai_advisor.fixed_template_explanation(facts)
    assert "explanation was unavailable" in explanation.summary


# ---------------------------------------------------------------------------
# Things the model is never allowed to decide
# ---------------------------------------------------------------------------


def test_confidence_comes_from_the_scoring_engine_not_the_model(db_session, seeded_lake):
    # A model claiming perfect confidence must not change the reported
    # number: confidence is the share of intended signal that had data.
    provider = _ScriptedProvider(
        json.dumps(
            {
                "summary": "Totally certain about everything.",
                "confidence": 1.0,
                "gear": [],
                "bait": [],
                "steps": [],
                "risks": [],
                "sources": [],
            }
        )
    )
    result = ai_advisor.explain(
        db_session,
        waterbody_id=seeded_lake["waterbody"].id,
        weather=_snapshot(),
        provider=provider,
    )
    server_fields = ai_advisor.server_controlled_fields(result.facts)

    assert result.answer_source == "llm"
    # There is no `confidence` field on the explanation at all to carry it.
    assert not hasattr(result.explanation, "confidence")
    assert server_fields["confidence"] == result.facts["candidates"][0]["confidence"]
    assert server_fields["confidence"] < 1.0  # only one forecast hour: no front signal


def test_safety_warnings_survive_a_model_that_ignores_them(db_session, seeded_lake):
    alert = WeatherAlert(
        event="Severe Thunderstorm Warning",
        severity="Severe",
        headline="Until 8 PM",
        effective=None,
        expires=None,
    )
    provider = _ScriptedProvider(
        json.dumps(
            {
                "summary": "Beautiful day, no concerns at all.",
                "gear": [],
                "bait": [],
                "steps": [],
                "risks": [],  # model dropped the warning entirely
                "sources": [],
            }
        )
    )
    result = ai_advisor.explain(
        db_session,
        waterbody_id=seeded_lake["waterbody"].id,
        weather=_snapshot(alerts=[alert]),
        provider=provider,
    )
    server_fields = ai_advisor.server_controlled_fields(result.facts)

    # The warning reaches the caller regardless of what the model wrote,
    # because it never went through the model in the first place (PRD
    # constraint 5: weather warnings outrank fishing advice).
    assert server_fields["safety_warnings"][0]["event"] == "Severe Thunderstorm Warning"


# ---------------------------------------------------------------------------
# Facts + caching
# ---------------------------------------------------------------------------


def test_gathered_facts_carry_evidence_and_sources_for_every_species(db_session, seeded_lake):
    facts = ai_advisor.gather_facts(
        db_session, seeded_lake["waterbody"].id, weather=_snapshot()
    )
    assert facts["species_confirmed_here"]
    for entry in facts["species_confirmed_here"]:
        assert entry["evidence"]
        assert entry["source_url"]


def test_prompt_contains_no_internal_plumbing_keys(db_session, seeded_lake):
    facts = ai_advisor.gather_facts(
        db_session, seeded_lake["waterbody"].id, weather=_snapshot()
    )
    prompt = ai_advisor.build_user_prompt(facts)
    assert "_recommendations" not in prompt
    assert "<facts>" in prompt


def test_identical_facts_hit_the_cache(db_session, seeded_lake):
    provider = _ScriptedProvider(
        json.dumps(
            {
                "summary": "Cached answer.",
                "gear": [],
                "bait": [],
                "steps": [],
                "risks": [],
                "sources": [],
            }
        )
    )
    kwargs = {
        "waterbody_id": seeded_lake["waterbody"].id,
        "weather": _snapshot(),
        "provider": provider,
    }
    first = ai_advisor.explain(db_session, **kwargs)
    second = ai_advisor.explain(db_session, **kwargs)

    assert provider.calls == 1
    assert second.trace.cache_hit is True
    assert first.trace.cache_hit is False
    # A cache hit still gets its own trace_id — two requests happened.
    assert first.trace.trace_id != second.trace.trace_id


def test_changed_facts_miss_the_cache(db_session, seeded_lake):
    provider = _ScriptedProvider(
        json.dumps(
            {
                "summary": "An answer.",
                "gear": [],
                "bait": [],
                "steps": [],
                "risks": [],
                "sources": [],
            }
        )
    )
    ai_advisor.explain(
        db_session,
        waterbody_id=seeded_lake["waterbody"].id,
        weather=_snapshot(),
        provider=provider,
    )
    # New access point -> different candidates -> different facts.
    db_session.add(
        AccessPoint(
            waterbody_id=seeded_lake["waterbody"].id,
            name="Second Ramp",
            latitude=32.84,
            longitude=-95.58,
            access_type="boat_ramp",
            public_status="confirmed_public",
            parking=True,
        )
    )
    db_session.commit()
    ai_advisor.explain(
        db_session,
        waterbody_id=seeded_lake["waterbody"].id,
        weather=_snapshot(),
        provider=provider,
    )

    assert provider.calls == 2


def test_a_fallback_is_not_cached(db_session, seeded_lake):
    """One bad moment shouldn't serve a degraded answer for 15 minutes."""
    good = json.dumps(
        {
            "summary": "A real answer.",
            "gear": [],
            "bait": [],
            "steps": [],
            "risks": [],
            "sources": [],
        }
    )
    provider = _ScriptedProvider("garbage", "garbage", good)
    kwargs = {
        "waterbody_id": seeded_lake["waterbody"].id,
        "weather": _snapshot(),
        "provider": provider,
    }
    first = ai_advisor.explain(db_session, **kwargs)
    second = ai_advisor.explain(db_session, **kwargs)

    assert first.answer_source == "fallback"
    assert second.answer_source == "llm"


# ---------------------------------------------------------------------------
# Trace (PRD constraint 14)
# ---------------------------------------------------------------------------


def test_trace_records_what_a_reviewer_would_ask_about(db_session, seeded_lake):
    result = ai_advisor.explain(
        db_session,
        waterbody_id=seeded_lake["waterbody"].id,
        weather=_snapshot(),
        provider=MockProvider(),
    )
    trace = result.trace

    assert trace.trace_id
    assert trace.provider == "mock"
    assert trace.model == "mock-advisor-v1"
    assert trace.prompt_tokens > 0
    assert trace.completion_tokens > 0
    assert trace.validation_attempts == 1
    assert trace.retrieved_source_count == len(result.facts["sources"])
    assert trace.retrieved_sources


def test_each_request_gets_its_own_trace_id(db_session, seeded_lake):
    ids = {
        ai_advisor.explain(
            db_session,
            waterbody_id=seeded_lake["waterbody"].id,
            weather=_snapshot(),
            provider=MockProvider(),
        ).trace.trace_id
        for _ in range(3)
    }
    assert len(ids) == 3


# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------


def test_explain_endpoint_returns_the_full_shape(client, seeded_lake, monkeypatch):
    # Stub the adapter the recommendations service reaches for, so the route
    # runs end to end without touching the network — same approach as
    # test_recommendations_api.py.
    monkeypatch.setattr(rec_module, "get_weather", lambda lat, lng: _snapshot())

    resp = client.post(
        "/api/advisor/explain",
        json={"waterbody_id": seeded_lake["waterbody"].id, "target_species": "Largemouth Bass"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["answer_source"] in {"llm", "fallback"}
    assert body["trace"]["trace_id"]
    assert "summary" in body["explanation"]
    # Server-controlled fields sit outside the model-authored explanation.
    assert "confidence" not in body["explanation"]
    assert isinstance(body["confidence"], float)
    assert isinstance(body["safety_warnings"], list)


def test_explain_endpoint_404s_for_an_unknown_lake(client):
    resp = client.post("/api/advisor/explain", json={"waterbody_id": 99999})
    assert resp.status_code == 404
