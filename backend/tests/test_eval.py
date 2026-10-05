"""Tests for the PRD §15 eval harness itself.

Two levels: the metrics arithmetic (fed synthetic results, so it's checked
independent of the advisor actually running), and an end-to-end run of the
real case list against the real advisor + mock provider, which is the
regression test that matters most here — if a future change to ai_advisor.py
ever let a hallucinated citation or species through, this is what would
catch it before a person did.
"""
from __future__ import annotations

from app.eval.cases import CASES, CATEGORY_ADVERSARIAL, CATEGORY_HAPPY
from app.eval.metrics import EvalCaseResult, compute_report
from app.eval.runner import run_eval
from app.services.ai_advisor import OUTCOME_OK


def _result(**overrides) -> EvalCaseResult:
    defaults = dict(
        case_id="x",
        description="",
        category=CATEGORY_HAPPY,
        expected_outcome=OUTCOME_OK,
        actual_outcome=OUTCOME_OK,
        expected_answer_source="llm",
        actual_answer_source="llm",
        passed=True,
        retrieval_hit=True,
        latency_ms=10.0,
        prompt_tokens=100,
        completion_tokens=20,
        estimated_cost_usd=0.0004,
    )
    defaults.update(overrides)
    return EvalCaseResult(**defaults)


def test_compute_report_rejects_an_empty_result_list():
    import pytest

    with pytest.raises(ValueError):
        compute_report([], CASES)


def test_pass_rate_and_failures_are_computed_from_the_results():
    results = [
        _result(case_id="a", passed=True),
        _result(case_id="b", passed=False, actual_outcome="ungrounded_source", actual_answer_source="fallback"),
    ]
    report = compute_report(results, CASES)
    assert report.total_cases == 2
    assert report.passed_cases == 1
    assert report.pass_rate == 0.5
    assert len(report.failures) == 1
    assert "b:" in report.failures[0]


def test_adversarial_catch_rate_only_counts_adversarial_cases():
    results = [
        _result(case_id="happy", category=CATEGORY_HAPPY, passed=True),
        _result(case_id="attack1", category=CATEGORY_ADVERSARIAL, passed=True),
        _result(case_id="attack2", category=CATEGORY_ADVERSARIAL, passed=False),
    ]
    report = compute_report(results, CASES)
    assert report.adversarial_total == 2
    assert report.adversarial_caught == 1
    assert report.adversarial_catch_rate == 0.5


def test_fallback_rate_happy_path_ignores_adversarial_cases():
    results = [
        _result(case_id="happy", category=CATEGORY_HAPPY, actual_answer_source="llm"),
        _result(
            case_id="attack",
            category=CATEGORY_ADVERSARIAL,
            actual_answer_source="fallback",
            passed=True,
        ),
    ]
    report = compute_report(results, CASES)
    assert report.fallback_rate_happy_path == 0.0
    assert report.fallback_rate_overall == 0.5


def test_retrieval_hit_rate_excludes_adversarial_cases():
    results = [
        _result(case_id="happy", category=CATEGORY_HAPPY, retrieval_hit=True),
        _result(case_id="edge", category="edge", retrieval_hit=False),
        _result(case_id="attack", category=CATEGORY_ADVERSARIAL, retrieval_hit=False, passed=True),
    ]
    report = compute_report(results, CASES)
    # Only the two non-adversarial cases count: 1 hit / 2 = 50%.
    assert report.retrieval_hit_rate == 0.5


def test_p95_latency_uses_the_slowest_observed_case():
    results = [_result(case_id=str(i), latency_ms=float(i)) for i in range(1, 21)]
    report = compute_report(results, CASES)
    assert report.p95_latency_ms == 19.0  # nearest-rank p95 of 1..20


def test_full_eval_run_passes_every_case_and_catches_every_adversarial_one():
    """The regression test: run the real case list against the real advisor.

    A future change that let a fabricated citation or species through would
    fail this without anyone having to notice it in a demo first.
    """
    results, report = run_eval()

    assert len(results) == len(CASES)
    assert report.pass_rate == 1.0, report.failures
    assert report.adversarial_catch_rate == 1.0
    assert report.fallback_rate_happy_path == 0.0
    assert report.retrieval_hit_rate == 1.0


def test_full_eval_run_is_deterministic():
    """The mock provider and fixtures are both hand-built with no randomness,
    so a second run must produce the identical outcome per case — a flaky
    eval suite would be worse than no eval suite."""
    results_a, _ = run_eval()
    results_b, _ = run_eval()
    assert [(r.case_id, r.actual_outcome, r.actual_answer_source) for r in results_a] == [
        (r.case_id, r.actual_outcome, r.actual_answer_source) for r in results_b
    ]
