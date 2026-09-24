"""The fixed scenario list PRD §15's metrics are computed over.

Ten cases, in three categories:
  - "happy":       the ordinary path, nothing should degrade.
  - "edge":        real situations that are not failures — an unconfirmed
                    species requested, stale weather, an active alert, a
                    closed lake with nothing to rank — and must still end
                    in a validated answer, not a fallback.
  - "adversarial": the four MockProvider failure modes, each of which must
                    be caught by validation/grounding and produce the fixed
                    fallback, never a discarded-but-shown answer.

This list is deliberately small and hand-picked rather than generated: the
point of an eval suite for a system whose entire premise is "don't trust the
model" is that a human can read every case and agree it's testing the right
thing, not that it has broad statistical coverage.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.ai_advisor import (
    OUTCOME_INVALID_JSON,
    OUTCOME_OK,
    OUTCOME_PROVIDER_UNAVAILABLE,
    OUTCOME_UNGROUNDED_SOURCE,
    OUTCOME_UNGROUNDED_SPECIES,
)
from app.services.llm.mock import (
    FAILURE_HALLUCINATED_SOURCE,
    FAILURE_HALLUCINATED_SPECIES,
    FAILURE_INVALID_JSON,
    FAILURE_NONE,
    FAILURE_UNAVAILABLE,
)

from .fixtures import UNCONFIRMED_SPECIES

CATEGORY_HAPPY = "happy"
CATEGORY_EDGE = "edge"
CATEGORY_ADVERSARIAL = "adversarial"


@dataclass(frozen=True)
class EvalCase:
    id: str
    description: str
    category: str
    waterbody: str  # "open" | "closed" — see fixtures.EvalFixtureIds
    target_species: str | None = None
    weather_source: str = "nws"  # "nws" | "fallback"
    has_safety_alert: bool = False
    failure_mode: str = FAILURE_NONE
    expect_outcome: str = OUTCOME_OK
    expect_answer_source: str = "llm"  # "llm" | "fallback"


CASES: list[EvalCase] = [
    EvalCase(
        id="happy_no_species",
        description="Ordinary request, no target species named.",
        category=CATEGORY_HAPPY,
        waterbody="open",
    ),
    EvalCase(
        id="happy_with_confirmed_species",
        description="Target species is confirmed in this lake.",
        category=CATEGORY_HAPPY,
        waterbody="open",
        target_species="Largemouth Bass",
    ),
    EvalCase(
        id="target_species_not_confirmed_here",
        description=(
            "Target species named is in the system's vocabulary but not "
            "confirmed for this lake. This is NOT an adversarial case — no "
            "failure_mode is injected — yet it still must end in the "
            "fallback: even an honest provider naturally phrases a targeted "
            "recommendation as being 'for' the requested species, which "
            "asserts presence the lake's own data doesn't confirm. Catching "
            "this in ordinary use, not just under a simulated attack, is a "
            "stronger proof of constraint 1 than the adversarial cases alone."
        ),
        category=CATEGORY_EDGE,
        waterbody="open",
        target_species=UNCONFIRMED_SPECIES,
        expect_outcome=OUTCOME_UNGROUNDED_SPECIES,
        expect_answer_source="fallback",
    ),
    EvalCase(
        id="weather_fallback",
        description="Live weather is unavailable; scoring runs without it.",
        category=CATEGORY_EDGE,
        waterbody="open",
        weather_source="fallback",
    ),
    EvalCase(
        id="active_safety_alert",
        description=(
            "A severe-weather alert is active. safety_warnings must reach "
            "the response regardless of what the model wrote (it never sees "
            "a field to put them in — see schemas/advisor.py)."
        ),
        category=CATEGORY_EDGE,
        waterbody="open",
        has_safety_alert=True,
    ),
    EvalCase(
        id="closed_lake_no_candidates",
        description=(
            "Closed lake, zero confirmed-public access points. The "
            "explanation must say there's nothing to rank, not invent a spot."
        ),
        category=CATEGORY_EDGE,
        waterbody="closed",
    ),
    EvalCase(
        id="provider_outage",
        description="The provider is down; must fall back without retrying it.",
        category=CATEGORY_ADVERSARIAL,
        waterbody="open",
        failure_mode=FAILURE_UNAVAILABLE,
        expect_outcome=OUTCOME_PROVIDER_UNAVAILABLE,
        expect_answer_source="fallback",
    ),
    EvalCase(
        id="invalid_json",
        description="The model's reply isn't parseable JSON, even after a retry.",
        category=CATEGORY_ADVERSARIAL,
        waterbody="open",
        failure_mode=FAILURE_INVALID_JSON,
        expect_outcome=OUTCOME_INVALID_JSON,
        expect_answer_source="fallback",
    ),
    EvalCase(
        id="hallucinated_source",
        description="The model cites a URL never supplied in the facts.",
        category=CATEGORY_ADVERSARIAL,
        waterbody="open",
        failure_mode=FAILURE_HALLUCINATED_SOURCE,
        expect_outcome=OUTCOME_UNGROUNDED_SOURCE,
        expect_answer_source="fallback",
    ),
    EvalCase(
        id="hallucinated_species",
        description="The model names a fish not confirmed in this lake (constraint 1).",
        category=CATEGORY_ADVERSARIAL,
        waterbody="open",
        failure_mode=FAILURE_HALLUCINATED_SPECIES,
        expect_outcome=OUTCOME_UNGROUNDED_SPECIES,
        expect_answer_source="fallback",
    ),
]
