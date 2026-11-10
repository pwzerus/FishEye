"""The question library (app/knowledge/angling_qa.py) and Ask's second tier
(services/rag/question_library.py, docs/adr/0051)."""
import re

import pytest
from fastapi.testclient import TestClient

from app.eval.rag_cases import OFF_TOPIC, ZH_OFF_TOPIC
from app.knowledge.angling_qa import BASES, CATEGORIES, ITEMS, get_item
from app.knowledge.species_guides import SOURCES
from app.main import app
from app.services.rag import ask as rag
from app.services.rag import question_library as ql
from app.services.rag.retriever import ScoredPassage, bm25_retriever

NUMBER = re.compile(r"\d+(?:[.:/]\d+)*½?|½")


@pytest.fixture(scope="module")
def library() -> ql.QuestionLibrary:
    return ql.library(None)


def test_every_answer_is_complete_in_both_languages():
    assert len(ITEMS) == 494
    assert len({i.id for i in ITEMS}) == len(ITEMS)
    for i in ITEMS:
        assert i.id.startswith("qa-"), i.id
        assert i.category in CATEGORIES, i.id
        assert i.basis in BASES, i.id
        assert all([i.question, i.question_zh, i.short, i.body, i.short_zh, i.body_zh]), i.id
        assert all(s in SOURCES for s in i.source_ids), i.id


def test_numbers_match_between_the_languages():
    for i in ITEMS:
        en = set(NUMBER.findall(f"{i.short} {i.body}"))
        zh = set(NUMBER.findall(f"{i.short_zh}{i.body_zh}"))
        assert en == zh, i.id


def test_a_sourced_basis_has_sources_or_is_fisheyes_own_data():
    for i in ITEMS:
        if i.basis in ("official", "maker"):
            assert i.source_ids, i.id


def test_no_forum_is_a_source_or_mentioned():
    """A forum answer is never a source (the data-sourcing skill's rule)."""
    assert not [s for s in SOURCES if s.startswith(("qa-forum-", "qa-site-"))]
    banned = re.compile(r"reddit|forum|论坛", re.I)
    for i in ITEMS:
        assert not banned.search(" ".join([i.question, i.question_zh, i.short, i.body, i.short_zh, i.body_zh])), i.id


def test_each_question_finds_its_own_answer(library):
    missed = [i.id for i in ITEMS if i.id not in [f.passage.section for f in library.search(i.question)[:2]]]
    assert not missed


def test_a_chinese_question_finds_its_own_answer(library):
    found = [i.id in [f.passage.section for f in library.search(i.question_zh)[:2]] for i in ITEMS]
    assert sum(found) / len(found) >= 0.98


@pytest.mark.parametrize("question", [*OFF_TOPIC, *ZH_OFF_TOPIC, "how do I fix a film reel projector", "best guitar strings for bass"])
def test_off_topic_questions_find_nothing(library, question):
    assert library.search(question) == []


def _hit(pid: str) -> ScoredPassage:
    passage = next(p for p in bm25_retriever().passages if p.id == pid)
    return ScoredPassage(passage, 1.0)


def test_a_state_rule_answer_is_left_alone():
    hits = [_hit("all-fish#rule-license-al")]
    assert ql.merge(hits, "What does the anti-reverse switch do?", 4, bm25_retriever()) == hits


def test_a_close_question_goes_on_top_without_pushing_a_guide_card_out():
    hits = [_hit(p.id) for p in bm25_retriever().passages[:4]]
    merged = ql.merge(hits, "What does the anti-reverse switch do?", 4, bm25_retriever())
    assert merged[0].passage.section == "qa-fb-reels-2"
    assert [h.passage.id for h in merged[1:]] == [h.passage.id for h in hits]


def test_ask_answers_what_the_guides_do_not_cover():
    result = rag.search_guides("Are subscription tackle boxes a good gift?", retriever=bm25_retriever())
    assert result.citations[0].section == "qa-gear-gift-4"
    assert result.citations[0].basis == "general"


@pytest.fixture()
def client():
    return TestClient(app)


def test_the_page_gets_the_language_it_asks_for(client):
    english = client.get("/api/species/questions").json()
    chinese = client.get("/api/species/questions?lang=zh").json()
    assert len(english) == len(chinese) == len(ITEMS)
    item = get_item(english[0]["id"])
    assert english[0]["question"] == item.question
    assert chinese[0]["question"] == item.question_zh
    assert chinese[0]["category_label"] == CATEGORIES[item.category]["zh"]


def test_sources_are_listed_once(client):
    rows = client.get("/api/species/questions/sources").json()
    urls = [r["url"] for r in rows]
    assert rows and len(urls) == len(set(urls))


def test_ask_cites_the_library_in_the_readers_language(client):
    body = client.post("/api/ask", json={"question": "订阅式渔具盒适合当礼物吗？", "lang": "zh"}).json()
    first = body["citations"][0]
    assert first["section"] == "qa-gear-gift-4"
    assert first["lang"] == "zh"
    assert first["title"] == get_item("qa-gear-gift-4").question_zh
