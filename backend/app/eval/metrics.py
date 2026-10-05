"""Turn a list of per-case results into the PRD §15 report.

PRD §15 asks, at minimum, for: retrieval hit rate, citation correctness,
factual consistency, tool-call success rate, JSON compliance rate, p95
latency, and per-request cost. Two of those don't map onto this system
literally, and the report says so rather than faking a number:

- "Citation correctness" and "factual consistency" are enforced by
  construction here (parse_and_validate rejects anything that fails either
  check, full stop — see ai_advisor.py), so on every *accepted* answer they
  are 100% by definition. The number worth reporting is instead how many of
  the adversarial cases designed to violate them were actually caught
  (`adversarial_catch_rate`) — that's the one that can fail.
- "Tool-call success rate" presumes the §13 tool-calling agent path, which
  was never built (the user chose §5.1's RAG-explanation path first). The
  closest analog for the flow that *does* exist is how often a request had
  to fall back at all (`fallback_rate`), reported both overall and for the
  happy-path cases alone (which should be 0% — any fallback there is a real
  regression, not an adversarial case doing its job).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .cases import CATEGORY_ADVERSARIAL, CATEGORY_HAPPY, EvalCase


@dataclass
class EvalCaseResult:
    case_id: str
    description: str
    category: str
    expected_outcome: str
    actual_outcome: str
    expected_answer_source: str
    actual_answer_source: str
    passed: bool
    retrieval_hit: bool
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    error: str | None = None


@dataclass
class EvalReport:
    total_cases: int
    passed_cases: int
    pass_rate: float
    retrieval_hit_rate: float
    adversarial_catch_rate: float
    adversarial_total: int
    adversarial_caught: int
    citation_and_factual_consistency_note: str
    fallback_rate_overall: float
    fallback_rate_happy_path: float
    tool_call_success_rate_note: str
    json_compliance_rate: float
    p50_latency_ms: float
    p95_latency_ms: float
    total_cost_usd: float
    avg_cost_usd: float
    failures: list[str] = field(default_factory=list)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    # Nearest-rank method: fine for the ~10-case suites this runs on, where
    # a fitted-interpolation percentile would imply more precision than a
    # 10-sample set actually has.
    rank = max(0, min(len(ordered) - 1, math.ceil(pct / 100 * len(ordered)) - 1))
    return ordered[rank]


def compute_report(results: list[EvalCaseResult], cases: list[EvalCase]) -> EvalReport:
    if not results:
        raise ValueError("no results to report on")

    total = len(results)
    passed = [r for r in results if r.passed]
    failures = [
        f"{r.case_id}: expected outcome={r.expected_outcome!r}/source={r.expected_answer_source!r}, "
        f"got outcome={r.actual_outcome!r}/source={r.actual_answer_source!r}"
        + (f" ({r.error})" if r.error else "")
        for r in results
        if not r.passed
    ]

    retrieval_candidates = [r for r in results if r.category != CATEGORY_ADVERSARIAL]
    retrieval_hit_rate = (
        sum(1 for r in retrieval_candidates if r.retrieval_hit) / len(retrieval_candidates)
        if retrieval_candidates
        else 0.0
    )

    adversarial = [r for r in results if r.category == CATEGORY_ADVERSARIAL]
    adversarial_caught = sum(1 for r in adversarial if r.passed)

    happy = [r for r in results if r.category == CATEGORY_HAPPY]
    fallback_overall = sum(1 for r in results if r.actual_answer_source == "fallback") / total
    fallback_happy = (
        sum(1 for r in happy if r.actual_answer_source == "fallback") / len(happy)
        if happy
        else 0.0
    )

    json_compliant = sum(1 for r in results if r.actual_outcome == "ok")
    latencies = [r.latency_ms for r in results]

    return EvalReport(
        total_cases=total,
        passed_cases=len(passed),
        pass_rate=len(passed) / total,
        retrieval_hit_rate=retrieval_hit_rate,
        adversarial_catch_rate=(adversarial_caught / len(adversarial)) if adversarial else 0.0,
        adversarial_total=len(adversarial),
        adversarial_caught=adversarial_caught,
        citation_and_factual_consistency_note=(
            "Enforced by construction: parse_and_validate() rejects any answer "
            "citing an unsupplied source or naming an unconfirmed species, so "
            "citation correctness and factual consistency are 100% on every "
            "accepted ('llm') answer by definition. See adversarial_catch_rate "
            "for the number that can actually fail."
        ),
        fallback_rate_overall=fallback_overall,
        fallback_rate_happy_path=fallback_happy,
        tool_call_success_rate_note=(
            "Not applicable: the PRD §13 tool-calling agent path was not built "
            "(the §5.1 RAG-explanation path was built first, per project "
            "decision). fallback_rate above is the closest analog for this flow."
        ),
        json_compliance_rate=json_compliant / total,
        p50_latency_ms=_percentile(latencies, 50),
        p95_latency_ms=_percentile(latencies, 95),
        total_cost_usd=sum(r.estimated_cost_usd for r in results),
        avg_cost_usd=sum(r.estimated_cost_usd for r in results) / total,
        failures=failures,
    )
