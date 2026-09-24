"""A deterministic stand-in for a real LLM.

Why this exists as a first-class provider rather than a test fixture
-------------------------------------------------------------------
1. Anyone cloning this repo can run the full advisor flow with zero API
   keys and zero spend — the same reasoning that picked Leaflet over the
   Google Maps JS API for the frontend. A demo a reviewer can't run is
   worth very little.
2. PRD §11's demo script calls for *showing* the degradation path
   ("switch to a failure scenario, simulate weather or LLM unavailable").
   You can't reliably demo a fallback by hoping a real model misbehaves on
   cue. `MOCK_FAILURE_MODE` makes each failure reproducible on demand.
3. It keeps the validation layer honest. This mock answers using only what
   the prompt gave it — so if it can produce a complete answer, the prompt
   really is self-contained, and a real model isn't being silently relied
   on to supply facts from its own weights. That's constraint 1 ("the LLM
   must not decide what fish are in a lake") enforced by construction.

It is never presented to a user as a real model: every response carries
provider="mock", and the API surfaces that so the UI can label it, exactly
like the weather adapter's `source: "fallback"`.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

from app.services.llm.base import LLMProvider, LLMResponse, LLMUnavailable

# The advisor wraps its structured facts in this fence so the mock can read
# back the same payload a real model would be reasoning over. Keeping the
# marker here (rather than in the prompt builder) puts it next to the only
# code that parses it.
FACTS_BLOCK_RE = re.compile(r"<facts>\s*(\{.*\})\s*</facts>", re.DOTALL)

# Failure modes, selectable at runtime for demos and asserted against in
# tests. "none" is the default everywhere except when explicitly set.
FAILURE_NONE = "none"
FAILURE_UNAVAILABLE = "unavailable"  # provider outage -> fixed-template fallback
FAILURE_INVALID_JSON = "invalid_json"  # unparseable -> retry, then fallback
FAILURE_HALLUCINATED_SOURCE = "hallucinated_source"  # cites a URL we never supplied
FAILURE_HALLUCINATED_SPECIES = "hallucinated_species"  # names a fish not in this lake


class MockProvider(LLMProvider):
    name = "mock"

    def __init__(self, failure_mode: str = FAILURE_NONE) -> None:
        self.failure_mode = failure_mode

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        started = time.perf_counter()

        if self.failure_mode == FAILURE_UNAVAILABLE:
            raise LLMUnavailable("mock provider: simulated outage")

        facts = self._read_facts(user_prompt)
        if self.failure_mode == FAILURE_INVALID_JSON:
            text = '{"summary": "truncated response with no closing brace'
        else:
            text = json.dumps(self._compose(facts), ensure_ascii=False)

        # Rough token accounting so the trace record has realistic shape.
        # ~4 chars/token is the usual English approximation; it is an
        # estimate in a mock, and labelled as one everywhere it surfaces.
        prompt_tokens = (len(system_prompt) + len(user_prompt)) // 4
        completion_tokens = len(text) // 4
        return LLMResponse(
            text=text,
            provider=self.name,
            model="mock-advisor-v1",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost_usd=0.0,  # genuinely free, not an unknown
            latency_ms=(time.perf_counter() - started) * 1000,
        )

    def _read_facts(self, user_prompt: str) -> dict[str, Any]:
        match = FACTS_BLOCK_RE.search(user_prompt)
        if match is None:
            # The prompt builder and this parser are a matched pair; if they
            # drift apart, that's a bug to surface, not to paper over with
            # an invented answer.
            raise LLMUnavailable("mock provider: no <facts> block in prompt")
        return json.loads(match.group(1))

    def _compose(self, facts: dict[str, Any]) -> dict[str, Any]:
        """Build an answer using only the supplied facts."""
        lake = facts.get("waterbody_name", "this lake")
        species = facts.get("target_species")
        candidates = facts.get("candidates", [])
        weather = facts.get("weather", {})
        window = facts.get("best_time_window")
        sources = [s["url"] for s in facts.get("sources", [])]

        top = candidates[0] if candidates else None
        species_phrase = f" for {species}" if species else ""

        if top is None:
            summary = (
                f"There are no confirmed-public access points on file for {lake} yet, "
                "so there is nothing to rank here."
            )
        else:
            summary = (
                f"{top['name']} is the strongest option{species_phrase} on {lake} right now. "
                f"{self._top_reason(top)}"
            )

        gear: list[str] = []
        bait: list[str] = []
        steps: list[str] = []

        if top is not None:
            access_type = str(top.get("access_type", "")).replace("_", " ")
            if access_type:
                steps.append(f"Start at {top['name']} ({access_type}).")
            wind = weather.get("wind_direction")
            downwind = weather.get("downwind_shore")
            if downwind:
                steps.append(
                    f"Wind is out of the {wind}, so work the {downwind} shore — "
                    "that is the bank the wind pushes bait toward."
                )
            if window:
                steps.append(f"Aim for the {window['reason'].lower()}")

            gear = ["A medium-power spinning rod covers most of what is listed here."]
            bait = ["Match whatever forage the lake's own survey notes mention."]

        risks: list[str] = []
        if weather.get("source") == "fallback":
            risks.append(
                "Live weather was unavailable, so nothing here accounts for current conditions."
            )

        if self.failure_mode == FAILURE_HALLUCINATED_SOURCE:
            sources = sources + ["https://example.com/made-up-fishing-blog"]
        if self.failure_mode == FAILURE_HALLUCINATED_SPECIES:
            summary += " Peacock Bass are also active in this lake right now."

        return {
            "summary": summary,
            "gear": gear,
            "bait": bait,
            "steps": steps,
            "risks": risks,
            "sources": sources,
        }

    @staticmethod
    def _top_reason(candidate: dict[str, Any]) -> str:
        """Quote the scoring engine's own reason for the strongest factor —
        the LLM's job here is to relay the rule engine's reasoning in plain
        language, never to invent a rationale of its own (PRD constraint 3).

        Only the leading clause is used. A factor reason is written for the
        `factors` list in the recommendations panel, where the full
        "...; little chance of rain (excluded: not enough forecast data to
        detect a front)" detail belongs; pasted whole into a one-line
        summary it reads as noise. A real model would condense it — the
        mock takes the first clause, which is the closest honest
        approximation of that without inventing wording that isn't in the
        source reason.
        """
        scored = [f for f in candidate.get("factors", []) if f.get("value") is not None]
        if not scored:
            return "No scored factors were available for it."
        best = max(scored, key=lambda f: f["value"] * f["weight"])
        lead_clause = str(best["reason"]).split(";")[0].strip()
        return f"The deciding factor was {best['name'].replace('_', ' ')}: {lead_clause}."
