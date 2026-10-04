"""Regression floor for guide Q&A retrieval (app/eval/rag_runner.py).

Thresholds sit a little below the measured numbers (hit@4 97%, MRR 0.87 on
30 questions when this was written) so that a genuine regression fails the
build but a single reworded case doesn't. The two that must stay at 100%
are the ones that protect users rather than rank passages.
"""
from app.eval.rag_cases import CASES
from app.eval.rag_runner import run


def test_retrieval_meets_its_floor():
    report = run()
    assert report.hit_at_k >= 0.9, report.misses
    assert report.mrr >= 0.75


def test_off_topic_questions_are_never_answered_from_the_guides():
    assert run().off_topic_rejection == 1.0


def test_a_named_fish_whose_guide_lacks_the_answer_gets_not_covered():
    # Not the nearest passage from another fish (that used to answer
    # "white bass vs hybrid" with the threadfin shad bait list).
    assert run().not_covered_rejection == 1.0


def test_every_injected_model_failure_is_caught():
    assert run().adversarial_caught == 1.0


def test_eval_case_ids_are_unique_and_labels_point_at_real_passages():
    from app.services.rag.chunking import build_passages

    ids = {p.id for p in build_passages()}
    assert len({c.id for c in CASES}) == len(CASES)
    for case in CASES:
        assert case.relevant <= ids, case.id
