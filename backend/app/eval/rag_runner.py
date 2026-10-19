"""Measure guide Q&A retrieval and grounding.

    python -m app.eval.rag_runner             # table + summary
    python -m app.eval.rag_runner --json      # machine-readable
    python -m app.eval.rag_runner --compare   # keyword vs hybrid, side by side

The Chinese and paraphrase sets (docs/adr/0025) are reported separately, so
the numbers on the original set stay comparable across ADRs.

Reports, for the retriever:
  - hit@K: share of questions with at least one relevant passage in the top K
    (K = ask.DEFAULT_K, what the model actually sees);
  - MRR: mean reciprocal rank of the first relevant passage (0 when missed);
  - off-topic rejection: share of off-topic questions that retrieve nothing,
    which is what lets ask.py answer "not covered" instead of improvising,
    and what keeps an off-topic question from spending an AI summary;
  - fishing admitted: share of fishing questions that name no fish which the
    on-topic gate still lets through (the other side of the same gate);
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
from app.services.rag.retriever import Retriever, bm25_retriever, default_retriever

from app.services.rag.chunking import SHARED_SLUG

from .rag_cases import (
    AMBIGUOUS_CASES,
    CASES,
    HOLDOUT_CASES,
    NEW_TOPIC_CASES,
    STRESS_CASES,
    NOT_COVERED,
    OFF_TOPIC,
    PARAPHRASE_CASES,
    UNNAMED_FISHING,
    ZH_CASES,
    ZH_NOT_COVERED,
    ZH_OFF_TOPIC,
    RagCase,
    StressCase,
)

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
class SetScore:
    cases: int
    hit_at_k: float
    mrr: float
    misses: list[str]


@dataclass
class RagReport:
    retriever: str
    k: int
    cases: int
    hit_at_k: float
    mrr: float
    off_topic_rejection: float
    off_topic_leaks: list[str]
    fishing_admitted: float  # share of UNNAMED_FISHING the gate searches
    gate_misses: list[str]
    not_covered_rejection: float
    adversarial_caught: float
    misses: list[str]
    results: list[RagCaseResult]
    chinese: SetScore
    paraphrase: SetScore
    zh_off_topic_rejection: float
    zh_off_topic_leaks: list[str]
    zh_not_covered_rejection: float
    stress: SetScore
    holdout: SetScore
    new_topics: SetScore
    ambiguous_resolved: float
    ambiguous_wrong: list[str]
    wrong_fish: list[str]  # "<case id>: <passage ids about a fish not asked about>"


def _stress(retr: Retriever, cases: tuple[StressCase, ...], k: int, wrong: list[str]) -> SetScore:
    """hit@k and MRR like _score, plus any passage about a fish the question
    didn't ask about (the "what bait for bass" -> shad failure)."""
    ranks: list[int | None] = []
    for case in cases:
        hits = retr.search(case.question, k=k)
        ids = [h.passage.id for h in hits]
        ranks.append(next((i + 1 for i, pid in enumerate(ids) if pid in case.relevant), None))
        if case.fish:
            bad = [h.passage.id for h in hits if h.passage.species_slug not in case.fish | {SHARED_SLUG}]
            if bad:
                wrong.append(f"{case.id}: {', '.join(bad)}")
    n = len(cases)
    return SetScore(
        cases=n,
        hit_at_k=sum(r is not None for r in ranks) / n,
        mrr=sum(1 / r for r in ranks if r) / n,
        misses=[c.id for c, r in zip(cases, ranks, strict=True) if r is None],
    )


def _score(retr: Retriever, cases: tuple[RagCase, ...], k: int) -> tuple[SetScore, list[RagCaseResult]]:
    results: list[RagCaseResult] = []
    for case in cases:
        context = (case.species_context,) if case.species_context else None
        ids = [h.passage.id for h in retr.search(case.question, k=k, species=context)]
        rank = next((i + 1 for i, pid in enumerate(ids) if pid in case.relevant), None)
        results.append(RagCaseResult(case.id, case.question, rank is not None, rank, ids))
    n = len(results)
    score = SetScore(
        cases=n,
        hit_at_k=sum(r.hit for r in results) / n,
        mrr=sum(1 / r.rank for r in results if r.rank) / n,
        misses=[r.id for r in results if not r.hit],
    )
    return score, results


def run(retriever: Retriever | None = None, k: int = rag.DEFAULT_K) -> RagReport:
    retr = retriever or default_retriever()
    main_score, results = _score(retr, CASES, k)
    chinese, _ = _score(retr, ZH_CASES, k)
    paraphrase, _ = _score(retr, PARAPHRASE_CASES, k)
    zh_leaks = [q for q in ZH_OFF_TOPIC if retr.search(q, k=k)]
    zh_nc_ok = sum(1 for q in ZH_NOT_COVERED if not retr.search(q, k=k))
    new_topics, _ = _score(retr, NEW_TOPIC_CASES, k)
    ambiguous_wrong = [
        f"{cid}: {q} -> {', '.join(retr.resolve(q)[0]) or 'no fish'}"
        for cid, q, want in AMBIGUOUS_CASES
        if hasattr(retr, "resolve") and set(retr.resolve(q)[0]) != set(want)
    ]
    wrong: list[str] = []
    stress = _stress(retr, STRESS_CASES, k, wrong)
    holdout = _stress(retr, HOLDOUT_CASES, k, wrong)

    off_topic_leaks = [q for q in OFF_TOPIC if retr.search(q, k=k)]
    gate_misses = [q for q in UNNAMED_FISHING if not retr.search(q, k=k)]
    not_covered_ok = sum(1 for q in NOT_COVERED if not retr.search(q, k=k))

    caught = 0
    rag.reset_cache()
    for mode in ADVERSARIAL_MODES:
        result = rag.ask(CASES[0].question, provider=MockProvider(failure_mode=mode), retriever=retr)
        caught += result.answer_source == rag.ANSWER_FALLBACK
    rag.reset_cache()

    return RagReport(
        retriever=getattr(retr, "name", "bm25"),
        k=k,
        cases=main_score.cases,
        hit_at_k=main_score.hit_at_k,
        mrr=main_score.mrr,
        off_topic_rejection=1 - len(off_topic_leaks) / len(OFF_TOPIC),
        off_topic_leaks=off_topic_leaks,
        fishing_admitted=1 - len(gate_misses) / len(UNNAMED_FISHING),
        gate_misses=gate_misses,
        not_covered_rejection=not_covered_ok / len(NOT_COVERED),
        adversarial_caught=caught / len(ADVERSARIAL_MODES),
        misses=main_score.misses,
        results=results,
        chinese=chinese,
        paraphrase=paraphrase,
        zh_off_topic_rejection=1 - len(zh_leaks) / len(ZH_OFF_TOPIC),
        zh_off_topic_leaks=zh_leaks,
        zh_not_covered_rejection=zh_nc_ok / len(ZH_NOT_COVERED),
        stress=stress,
        holdout=holdout,
        new_topics=new_topics,
        ambiguous_resolved=1 - len(ambiguous_wrong) / len(AMBIGUOUS_CASES),
        ambiguous_wrong=ambiguous_wrong,
        wrong_fish=wrong,
    )


def _compare() -> int:
    retrievers = [bm25_retriever()]
    hybrid = default_retriever()
    if getattr(hybrid, "name", "bm25") == "bm25":
        print("Semantic retrieval isn't available (no model, or RAG_SEMANTIC=off); keyword only.")
    else:
        retrievers.append(hybrid)
    reports = [run(r) for r in retrievers]
    rows = [
        ("original set hit@4", lambda r: f"{r.hit_at_k:.0%}"),
        ("original set MRR", lambda r: f"{r.mrr:.2f}"),
        ("Chinese hit@4", lambda r: f"{r.chinese.hit_at_k:.0%}"),
        ("Chinese MRR", lambda r: f"{r.chinese.mrr:.2f}"),
        ("paraphrase hit@4", lambda r: f"{r.paraphrase.hit_at_k:.0%}"),
        ("paraphrase MRR", lambda r: f"{r.paraphrase.mrr:.2f}"),
        ("new topics hit@4", lambda r: f"{r.new_topics.hit_at_k:.0%}"),
        ("everyday-word names right", lambda r: f"{r.ambiguous_resolved:.0%}"),
        ("rephrased hit@4", lambda r: f"{r.stress.hit_at_k:.0%}"),
        ("rephrased, untuned hit@4", lambda r: f"{r.holdout.hit_at_k:.0%}"),
        ("wrong-fish answers", lambda r: f"{len(r.wrong_fish)}"),
        ("off-topic rejected", lambda r: f"{r.off_topic_rejection:.0%}"),
        ("Chinese off-topic rejected", lambda r: f"{r.zh_off_topic_rejection:.0%}"),
        ("unnamed fishing admitted", lambda r: f"{r.fishing_admitted:.0%}"),
        ("not covered (EN)", lambda r: f"{r.not_covered_rejection:.0%}"),
        ("not covered (ZH)", lambda r: f"{r.zh_not_covered_rejection:.0%}"),
    ]
    print(f"{'':28}" + "".join(f"{r.retriever:>10}" for r in reports))
    for label, fmt in rows:
        print(f"{label:28}" + "".join(f"{fmt(r):>10}" for r in reports))
    for r in reports:
        all_misses = (r.misses + r.chinese.misses + r.paraphrase.misses + r.stress.misses
                      + r.holdout.misses + r.new_topics.misses)
        print(f"\n[{r.retriever}] misses: {', '.join(all_misses) or '-'}")
        for w in r.wrong_fish:
            print(f"[{r.retriever}] wrong fish: {w}")
        for w in r.ambiguous_wrong:
            print(f"[{r.retriever}] everyday word: {w}")
        for q in r.off_topic_leaks + r.zh_off_topic_leaks:
            print(f"[{r.retriever}] searched anyway: {q}")
        for q in r.gate_misses:
            print(f"[{r.retriever}] turned away: {q}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--compare", action="store_true")
    args = parser.parse_args(argv)
    if args.compare:
        return _compare()
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
    print(f"off-topic rejected: {report.off_topic_rejection:.0%}  ({len(OFF_TOPIC)} questions)")
    for q in report.off_topic_leaks:
        print(f"    searched anyway: {q}")
    print(f"fishing admitted:   {report.fishing_admitted:.0%}  ({len(UNNAMED_FISHING)} questions naming no fish)")
    for q in report.gate_misses:
        print(f"    turned away:     {q}")
    print(f"not-covered rejected: {report.not_covered_rejection:.0%}")
    print(f"adversarial caught: {report.adversarial_caught:.0%}")
    if report.misses:
        print(f"misses:             {', '.join(report.misses)}")
    print(f"retriever:          {report.retriever}")
    print(f"Chinese hit@{report.k}:      {report.chinese.hit_at_k:.0%}  ({report.chinese.cases} questions)")
    print(f"paraphrase hit@{report.k}:   {report.paraphrase.hit_at_k:.0%}  ({report.paraphrase.cases} questions)")
    print(f"rephrased hit@{report.k}:    {report.stress.hit_at_k:.0%}  ({report.stress.cases}), "
          f"untuned {report.holdout.hit_at_k:.0%} ({report.holdout.cases})")
    print(f"new topics hit@{report.k}:   {report.new_topics.hit_at_k:.0%}  ({report.new_topics.cases} questions)")
    print(f"everyday-word names right: {report.ambiguous_resolved:.0%}  ({len(AMBIGUOUS_CASES)} questions)")
    print(f"wrong-fish answers: {len(report.wrong_fish)}")
    for w in report.wrong_fish:
        print(f"    {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
