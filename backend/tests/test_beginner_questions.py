"""What beginners ask (2026-11-08, docs/adr/0049).

177 beginner questions, written in our own words or paraphrased from forums,
were put to Ask. These tests pin what they turned up: the limits card for
every state, a second rod in California, words the topic gate turned away,
and the Chinese and Spanish words that found nothing. The questions
themselves are scored as an eval set (eval/rag_cases.BEGINNER_CASES)."""
import re

import pytest

from app.knowledge import jurisdictions as j
from app.knowledge.angling_handbook import TOPICS, get_topic
from app.knowledge.species_guides import SOURCES
from app.services.rag import ask as rag_ask
from app.services.rag import es, zh
from app.services.rag.retriever import is_on_topic

NEW_TOPICS = (
    "technique-bite", "technique-landing", "care-deep-hook", "trouble-no-bites", "trouble-stolen-bait", "trouble-snags",
    "trouble-line-twist", "rule-manners", "method-kids", "safe-lightning", "safe-heat", "safe-cold-water",
    # Second forum pass (docs/adr/0049, addendum).
    "care-fresh-or-spoiled", "safe-clothing",
)


def _ids(result):
    return [p.id for p in result.citations]


# ---------------------------------------------------------------- the cards


def test_the_new_topics_exist_and_cite_pages():
    for tid in NEW_TOPICS:
        t = get_topic(tid)
        assert t is not None, tid
        assert t.region == "all" and t.source_ids, tid
        assert all(SOURCES[s].url.startswith("https://") for s in t.source_ids), tid


def test_every_state_has_a_limits_card_pointing_at_its_own_limits_page():
    cards = {t.region: t for t in TOPICS if t.id.startswith("rule-limits-")}
    assert set(cards) == {code for code, s in j.JURISDICTIONS.items() if s.limits_url}
    for code, card in cards.items():
        state = j.JURISDICTIONS[code]
        assert card.id == f"rule-limits-{code.lower()}"
        assert state.name in card.title
        assert [SOURCES[s].url for s in card.source_ids] == [state.limits_url]
        # Where the numbers are, never the numbers: they change every year.
        assert not re.search(r"\d", " ".join(card.body)), card.id


# ------------------------------------------------------------------- Ask


@pytest.mark.parametrize(
    ("question", "state", "want"),
    [
        ("how many bass can I keep", "TX", "all-fish#rule-limits-tx"),
        ("how big does a bass have to be to keep it", "GA", "all-fish#rule-limits-ga"),
        ("what is the daily limit on crappie", "CA", "all-fish#rule-limits-ca"),
        ("how many catfish am I allowed to keep", "MN", "all-fish#rule-limits-mn"),
        ("德州鲈鱼能带走几条", "TX", "all-fish#rule-limits-tx"),
    ],
)
def test_a_limits_question_gets_that_states_limits_card(question, state, want):
    result = rag_ask.search_guides(question, state=state)
    assert want in _ids(result)[:2], _ids(result)


def test_a_question_that_only_says_keep_is_not_a_limits_question():
    for question in ("how do I keep minnows alive", "how do I keep my catch fresh"):
        assert not any(i.startswith("all-fish#rule-limits-") for i in _ids(rag_ask.search_guides(question, state="TX")))


def test_a_second_rod_in_california_gets_its_license_card():
    result = rag_ask.search_guides("can I fish with two rods at the same time", state="CA")
    assert _ids(result)[0] == "all-fish#rule-license-ca"
    assert "two rods" in result.citations[0].text


@pytest.mark.parametrize(
    "question",
    [
        "do I need a swivel",
        "my knot keeps coming undone",
        "how do I stop getting snagged all the time",
        "do I need a landing net",
        "what happens if I fall into cold water",
        "how many bass can I keep",
        "I haven't caught anything all year, what am I doing wrong",
        "are tungsten weights worth the money",
        "how long does braided line last before I need to replace it",
    ],
)
def test_beginner_questions_the_gate_used_to_turn_away(question):
    assert is_on_topic(question)


def test_chinese_and_spanish_words_the_glossaries_lacked():
    assert "drag" in zh.with_english("卸力应该调多紧")
    assert "snag" in zh.with_english("鱼钩挂底了怎么办")
    assert "lightning" in zh.with_english("打雷的时候还能钓鱼吗")
    english = es.to_english("¿Por qué no pican los peces?")
    assert "no bites" in english and "fish" in english
    assert "snagged" in es.to_english("Se me atoró el anzuelo en el fondo")
