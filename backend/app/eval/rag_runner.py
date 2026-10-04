"""Measure guide Q&A retrieval and grounding.

    python -m app.eval.rag_runner          # table + summary
    python -m app.eval.rag_runner --json   # machine-readable

Reports, for the retriever:
  - hit@K: share of questions with at least one relevant passage in the top K
    (K = ask.DEFAULT_K, what the model actually sees);
  - MRR: mean reciprocal rank of the first relevant passage (0 when missed);
  - off-topic rejection: share of off-topic questions that retrieve nothing,
    which is what lets ask.py answer "not covered" instead of improvising;
and, for the answer pipeline, how many of the mock's injected failures the
validator caught (every one should be).
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass

from app.services.llm.mock import (
    FAILURE_HALLUCINATED_SOURCE,
    FAILURE_HALLUCINATED_SPECIES,
    FAILURE_INVALID_JSON,
    FAILURE_INVENTED_NUMBER,
    MockProvider,
)
from app.services.rag import ask as rag
from app.services.rag.retriever import Retriever, default_retriever

from .rag_cases import CASES, NOT_COVERED, OFF_TOPIC

ADVERSARIAL_MODES = (
    FAILURE_HALLUCINATED_SOURCE,
    FAILURE_HALLUCINATED_SPECIES,
    FAILURE_INVENTED_NUMBER,
    FAILURE_INVALID_JSON,
)


@dataclass
class RagCaseResult:
    id: str
    question: str
    hit: bool
    rank: int | None  # 1-based rank of the first relevant passage
    retrieved: list[str]


@dataclass
class RagReport:
    k: int
    cases: int
    hit_at_k: float
    mrr: float
    off_topic_rejection: float
    not_covered_rejection: float
    adversarial_caught: float
    misses: list[str]
    results: list[RagCaseResult]


def run(retriever: Retriever | None = None, k: int = rag.DEFAULT_K) -> RagReport:
    retr = retriever or default_retriever()
    results: list[RagCaseResult] = []
    for case in CASES:
        context = (case.species_context,) if case.species_context else None
        ids = [h.passage.id for h in retr.search(case.question, k=k, species=context)]
        rank = next((i + 1 for i, pid in enumerate(ids) if pid in case.relevant), None)
        results.append(RagCaseResult(case.id, case.question, rank is not None, rank, ids))

    off_topic_ok = sum(1 for q in OFF_TOPIC if not retr.search(q, k=k))
    not_covered_ok = sum(1 for q in NOT_COVERED if not retr.search(q, k=k))

    caught = 0
    rag.reset_cache()
    for mode in ADVERSARIAL_MODES:
        result = rag.ask(CASES[0].question, provider=MockProvider(failure_mode=mode), retriever=retr)
        caught += result.answer_source == rag.ANSWER_FALLBACK
    rag.reset_cache()

    n = len(results)
    return RagReport(
        k=k,
        cases=n,
        hit_at_k=sum(r.hit for r in results) / n,
        mrr=sum(1 / r.rank for r in results if r.rank) / n,
        off_topic_rejection=off_topic_ok / len(OFF_TOPIC),
        not_covered_rejection=not_covered_ok / len(NOT_COVERED),
        adversarial_caught=caught / len(ADVERSARIAL_MODES),
        misses=[r.id for r in results if not r.hit],
        results=results,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = run()
    if args.json:
        print(json.dumps(asdict(report), indent=2))
        return 0
    for r in report.results:
        mark = f"#{r.rank}" if r.rank else "MISS"
        print(f"{mark:>5}  {r.id:<16} {r.question}")
    print()
    print(f"hit@{report.k}:              {report.hit_at_k:.0%}  ({report.cases} questions)")
    print(f"MRR:                {report.mrr:.2f}")
    print(f"off-topic rejected: {report.off_topic_rejection:.0%}")
    print(f"not-covered rejected: {report.not_covered_rejection:.0%}")
    print(f"adversarial caught: {report.adversarial_caught:.0%}")
    if report.misses:
        print(f"misses:             {', '.join(report.misses)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
