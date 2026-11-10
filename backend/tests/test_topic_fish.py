"""Fish the handbook covers but no guide does (steelhead, salmon, lake
trout, sturgeon, whitefish): answered from their topics, not refused."""
from __future__ import annotations

import pytest

from app.services.rag.retriever import bm25_retriever, is_on_topic, names_unguided_fish, topic_fish_passages


@pytest.mark.parametrize(
    "question, topic",
    [
        ("is a steelhead the same as a rainbow trout", "all-fish#id-steelhead-rainbow"),
        ("how do I tell a chinook from a coho", "all-fish#id-salmon"),
        ("when do salmon run", "all-fish#timing-runs"),
        ("what do lake trout eat", "all-fish#method-lake-trout"),
        ("how to catch a sturgeon", "all-fish#method-sturgeon"),
        ("cisco or whitefish", "all-fish#id-whitefish-cisco"),
        ("三文鱼怎么钓", "all-fish#id-salmon"),
        ("硬头鳟和虹鳟有什么区别", "all-fish#id-steelhead-rainbow"),
    ],
)
def test_a_topic_fish_gets_its_topic_first(question, topic):
    assert bm25_retriever().search(question, k=3)[0].passage.id == topic


def test_lake_trout_is_not_read_as_the_trout_guides():
    hits = bm25_retriever().search("what do lake trout eat", k=2)
    assert all(h.passage.id.startswith("all-fish#") for h in hits)


def test_topic_fish_are_fishing_questions_and_not_unguided():
    assert is_on_topic("steelhead") and is_on_topic("king salmon run")
    assert not names_unguided_fish("salmon tips")


def test_a_kitchen_question_about_salmon_stays_off_topic():
    assert topic_fish_passages("how do I cook salmon") == ()
    assert topic_fish_passages("what bait catches salmon I can grill")
