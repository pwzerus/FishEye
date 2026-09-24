"""Runs every EvalCase against the advisor and prints the PRD §15 report.

    python -m app.eval.runner            # human-readable table + summary
    python -m app.eval.runner --json     # machine-readable report

Runs entirely against the mock provider (see services/llm/mock.py) — there
is no real provider implemented yet, and this suite's job is to prove the
*pipeline* (grounding, retry, fallback, trace) behaves correctly, which the
mock's deterministic failure modes are built to exercise on demand.
"""
from __future__ import annotations

import argparse
import json as jsonlib
import sys
from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.services import ai_advisor
from app.services.llm import MockProvider
from app.services.weather_adapter import CurrentConditions, HourlyPeriod, WeatherAlert, WeatherSnapshot

from .cases import CASES, EvalCase
from .fixtures import EvalFixtureIds, build_eval_db
from .metrics import EvalCaseResult, EvalReport, compute_report

NOW = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)


def _weather_for(case: EvalCase) -> WeatherSnapshot:
    alerts = (
        [
            WeatherAlert(
                event="Severe Thunderstorm Warning",
                severity="severe",
                headline="Severe thunderstorms capable of damaging wind expected.",
                effective=NOW,
                expires=NOW,
            )
        ]
        if case.has_safety_alert
        else []
    )
    current = CurrentConditions(
        temperature=72,
        temperature_unit="F",
        wind_speed="10 mph",
        wind_direction="SE",
        short_forecast="Partly Sunny",
        is_daytime=True,
    )
    if case.weather_source == "fallback":
        return WeatherSnapshot(
            latitude=32.8,
            longitude=-95.6,
            current=current,
            hourly=[],
            alerts=alerts,
            source="fallback",
            stale=True,
            fetched_at=NOW,
        )
    return WeatherSnapshot(
        latitude=32.8,
        longitude=-95.6,
        current=current,
        hourly=[
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
        alerts=alerts,
        source="nws",
        stale=False,
        fetched_at=NOW,
    )


def run_case(db: Session, ids: EvalFixtureIds, case: EvalCase) -> EvalCaseResult:
    waterbody_id = ids.open_lake_id if case.waterbody == "open" else ids.closed_lake_id
    ai_advisor.reset_cache()  # each case is an independent trial

    try:
        result = ai_advisor.explain(
            db,
            waterbody_id,
            target_species=case.target_species,
            weather=_weather_for(case),
            provider=MockProvider(failure_mode=case.failure_mode),
        )
    except Exception as exc:  # a case erroring out is itself a failed case, not a crash
        return EvalCaseResult(
            case_id=case.id,
            description=case.description,
            category=case.category,
            expected_outcome=case.expect_outcome,
            actual_outcome="error",
            expected_answer_source=case.expect_answer_source,
            actual_answer_source="error",
            passed=False,
            retrieval_hit=False,
            latency_ms=0.0,
            prompt_tokens=0,
            completion_tokens=0,
            estimated_cost_usd=0.0,
            error=repr(exc),
        )

    passed = (
        result.trace.outcome == case.expect_outcome
        and result.answer_source == case.expect_answer_source
    )

    # For the active-safety-alert case, also require the warning actually
    # reached the response — that's the entire point of the case, and a case
    # that only checked trace.outcome would pass even if this regressed.
    if case.has_safety_alert:
        fields = ai_advisor.server_controlled_fields(result.facts)
        passed = passed and len(fields["safety_warnings"]) > 0

    # "Retrieval" here means: for a lake with data to retrieve, did the facts
    # payload actually carry sources and species evidence? A closed lake with
    # nothing on file has nothing to retrieve, so it's excluded (see
    # metrics.compute_report), not scored as a miss.
    retrieval_hit = bool(result.facts.get("sources")) and (
        case.waterbody != "open" or bool(result.facts.get("species_confirmed_here"))
    )

    return EvalCaseResult(
        case_id=case.id,
        description=case.description,
        category=case.category,
        expected_outcome=case.expect_outcome,
        actual_outcome=result.trace.outcome,
        expected_answer_source=case.expect_answer_source,
        actual_answer_source=result.answer_source,
        passed=passed,
        retrieval_hit=retrieval_hit,
        latency_ms=result.trace.latency_ms,
        prompt_tokens=result.trace.prompt_tokens,
        completion_tokens=result.trace.completion_tokens,
        estimated_cost_usd=result.trace.estimated_cost_usd,
    )


def run_eval() -> tuple[list[EvalCaseResult], EvalReport]:
    db, ids = build_eval_db()
    try:
        results = [run_case(db, ids, case) for case in CASES]
    finally:
        db.close()
    report = compute_report(results, CASES)
    return results, report


def _print_table(results: list[EvalCaseResult]) -> None:
    header = f"{'case':<32} {'category':<12} {'expected':<24} {'actual':<24} {'pass':<5} {'ms':>7} {'$':>10}"
    print(header)
    print("-" * len(header))
    for r in results:
        expected = f"{r.expected_outcome}/{r.expected_answer_source}"
        actual = f"{r.actual_outcome}/{r.actual_answer_source}"
        print(
            f"{r.case_id:<32} {r.category:<12} {expected:<24} {actual:<24} "
            f"{'yes' if r.passed else 'NO':<5} {r.latency_ms:>7.2f} {r.estimated_cost_usd:>10.6f}"
        )


def _print_summary(report: EvalReport) -> None:
    print()
    print(f"pass rate:              {report.passed_cases}/{report.total_cases} ({report.pass_rate:.0%})")
    print(f"retrieval hit rate:     {report.retrieval_hit_rate:.0%}")
    print(
        f"adversarial catch rate: {report.adversarial_caught}/{report.adversarial_total} "
        f"({report.adversarial_catch_rate:.0%})"
    )
    print(f"  note: {report.citation_and_factual_consistency_note}")
    print(f"json compliance rate:   {report.json_compliance_rate:.0%}")
    print(f"fallback rate (all):    {report.fallback_rate_overall:.0%}")
    print(f"fallback rate (happy):  {report.fallback_rate_happy_path:.0%}")
    print(f"  note: {report.tool_call_success_rate_note}")
    print(f"p50 / p95 latency:      {report.p50_latency_ms:.2f} ms / {report.p95_latency_ms:.2f} ms")
    print(f"total / avg cost:       ${report.total_cost_usd:.6f} / ${report.avg_cost_usd:.6f}")
    if report.failures:
        print()
        print("failures:")
        for f in report.failures:
            print(f"  - {f}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the report as JSON instead of a table")
    args = parser.parse_args(argv)

    results, report = run_eval()

    if args.json:
        print(jsonlib.dumps({"results": [asdict(r) for r in results], "report": asdict(report)}, indent=2))
    else:
        _print_table(results)
        _print_summary(report)

    return 0 if report.pass_rate == 1.0 else 1


if __name__ == "__main__":
    sys.exit(main())
