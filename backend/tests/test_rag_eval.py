"""Regression floor for guide Q&A retrieval (app/eval/rag_runner.py).

Thresholds sit a little below the measured numbers (hit@4 97%, MRR 0.87 on
30 questions when this was written) so that a genuine regression fails the
build but a single reworded case doesn't. The two that must stay at 100%
are the ones that protect users rather than rank passages.

The off-topic set is deliberately hard (words shared with fishing) and is
held to 95%, not 100%: "recommend a hook for my song" gets through, because
counting "hook" as a fishing word is what lets "what size hook should I
use" through, and the beginner's question matters more. Measured: 1 of 24
off-topic questions searched, 14 of 15 unnamed fishing questions admitted.
"""
from app.eval.rag_cases import CASES
from app.eval.rag_runner import run


def test_retrieval_meets_its_floor():
    report = run()
    assert report.hit_at_k >= 0.9, report.misses
    assert report.mrr >= 0.75


def test_off_topic_questions_are_almost_never_searched():
    report = run()
    assert report.off_topic_rejection >= 0.95, report.off_topic_leaks


def test_the_on_topic_gate_still_admits_fishing_questions_that_name_no_fish():
    report = run()
    assert report.fishing_admitted >= 0.9, report.gate_misses


def test_a_named_fish_whose_guide_lacks_the_answer_gets_not_covered():
    # Not the nearest passage from another fish (that used to answer
    # "white bass vs hybrid" with the threadfin shad bait list).
    assert run().not_covered_rejection == 1.0


def test_every_injected_model_failure_is_caught():
    assert run().adversarial_caught == 1.0


def test_eval_case_ids_are_unique_and_labels_point_at_real_passages():
    from app.eval.rag_cases import (
        HOLDOUT_CASES,
        NEW_TOPIC_CASES,
        PARAPHRASE_CASES,
        STRESS_CASES,
        ZH_CASES,
    )
    from app.services.rag.chunking import build_passages

    ids = {p.id for p in build_passages()}
    every = (*CASES, *ZH_CASES, *PARAPHRASE_CASES, *NEW_TOPIC_CASES, *STRESS_CASES, *HOLDOUT_CASES)
    assert len({c.id for c in every}) == len(every)
    for case in every:
        assert case.relevant <= ids, case.id


def test_keyword_search_answers_chinese_questions_through_the_glossary():
    # Keyword search alone, no model (docs/adr/0025): measured 100%.
    assert run().chinese.hit_at_k >= 0.9


def test_the_topics_added_with_adr_0026_are_reachable():
    report = run()
    assert report.new_topics.hit_at_k >= 0.8, report.new_topics.misses


def test_a_name_that_is_also_an_everyday_word_is_read_the_right_way():
    # bass/drum/blues/cats/slabs/spots in both senses. Keyword search alone
    # manages all but a couple; with the model it is all of them (ADR 0026).
    report = run()
    assert report.ambiguous_resolved >= 0.9, report.ambiguous_wrong


def test_rephrased_questions_still_find_their_passage_and_never_another_fish():
    # Measured with keyword search: 45/50 rephrased, 24/30 untuned, and one
    # wrong-fish answer (a texas-rig question that names no fish).
    report = run()
    assert report.stress.hit_at_k >= 0.85, report.stress.misses
    assert report.holdout.hit_at_k >= 0.75, report.holdout.misses
    assert len(report.wrong_fish) <= 1, report.wrong_fish
