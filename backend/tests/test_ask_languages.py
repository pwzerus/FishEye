"""Ask in Spanish, Korean and Japanese, and Ask's own words in the asker's
language (services/rag/es.py, ko.py, ja.py, replies.py)."""
from __future__ import annotations

import pytest

from app.services.rag import es, ja, ko, replies


@pytest.mark.parametrize(
    ("question", "spanish"),
    [
        ("¿Qué carnada uso para bagre?", True),
        ("que carnada uso para bagre", True),  # no accents typed
        ("Necesito licencia en Georgia", True),
        ("What bait for crappie?", False),
        ("钓鲶鱼用什么饵", False),
        ("crappie", False),
    ],
)
def test_spanish_is_told_apart(question, spanish):
    assert es.is_spanish(question) is spanish


def test_a_spanish_question_is_searched_in_the_guides_words():
    assert es.to_english("¿Qué carnada uso para bagre?") == "what bait use for catfish"
    assert es.to_english("¿Cómo pesco LOBINA NEGRA en la orilla?") == "how catch largemouth bass in la bank shore"
    # Longest phrase first: the bluegill isn't just any "mojarra".
    assert "bluegill" in es.to_english("mojarra de agallas azules")
    assert es.to_english("bagre de canal") == "channel catfish"


def test_replies_follow_the_question_then_the_site():
    assert replies.reply_lang("¿Qué carnada uso?", "en") == "es"
    assert replies.reply_lang("钓鲶鱼用什么饵", "es") == "zh"
    assert replies.reply_lang("crappie bait", "es") == "es"
    assert replies.reply_lang("crappie bait", "fr") == "en"
    assert replies.passages_intro("es").startswith("Esto es lo que dicen")


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("¿Qué carnada uso para bagre?", "channel-catfish#why_these_baits"),
        ("¿Cómo amarro un nudo de pesca?", "all-fish#knot-improved-clinch"),
        ("¿Necesito licencia de pesca en Georgia?", "all-fish#rule-license-ga"),
        ("¿Cuántos crappie me puedo quedar en Georgia?", "all-fish#care-possession-ga"),
    ],
)
def test_spanish_questions_find_the_passage(client, question, expected):
    body = client.post("/api/ask", json={"question": question, "lang": "es"}).json()
    assert body["answer_source"] == "passages", body
    assert expected in [c["id"] for c in body["citations"]]
    assert body["answer"].startswith("Esto es lo que dicen las guías")


def test_a_spanish_off_topic_question_is_declined_in_spanish(client):
    body = client.post("/api/ask", json={"question": "¿Cómo hago tacos de pollo?"}).json()
    assert body["answer_source"] == "no_match" and body["trace"]["outcome"] == "off_topic"
    assert body["answer"].startswith("Eso no parece una pregunta de pesca")


def test_an_english_question_on_the_chinese_site_is_introduced_in_chinese(client):
    body = client.post("/api/ask", json={"question": "what bait for crappie", "lang": "zh"}).json()
    assert body["answer_source"] == "passages"
    assert body["answer"] == replies.passages_intro("zh")


@pytest.mark.parametrize(
    ("question", "lang"),
    [
        ("ブルーギルの釣り方は？", "ja"),
        ("鯉の釣り方", "ja"),  # kanji, but the kana make it Japanese
        ("钓鲶鱼用什么饵", "zh"),
        ("블루길 미끼는 뭐가 좋아요?", "ko"),
        ("crappie bait", "en"),
    ],
)
def test_japanese_and_korean_are_told_apart(question, lang):
    assert replies.reply_lang(question, None) == lang


def test_japanese_and_korean_questions_are_searched_in_the_guides_words():
    assert ja.to_english("ブルーギルの針のサイズは？") == "bluegill hook size"
    assert ja.to_english("Lake Lanierでバスは釣れる？") == "lake lanier bass catch"
    assert ko.to_english("블루길 바늘 크기는요?") == "bluegill hook size"
    # A stew isn't a bobber, and nothing Korean reaches the Chinese rules.
    assert ko.to_english("김치찌개 만드는 방법") == ""


@pytest.mark.parametrize(
    ("question", "lang", "expected"),
    [
        ("ナマズには何のエサを使えばいい？", "ja", "channel-catfish#why_these_baits"),
        ("釣り糸の結び方は？", "ja", "all-fish#knot-improved-clinch"),
        ("ジョージア州で釣りライセンスは必要？", "ja", "all-fish#rule-license-ga"),
        ("ジョージア州でクラッピーは何匹持ち帰れる？", "ja", "all-fish#care-possession-ga"),
        ("메기 미끼는 뭐가 좋아요?", "ko", "channel-catfish#why_these_baits"),
        ("낚싯줄 매듭은 어떻게 묶어요?", "ko", "all-fish#knot-improved-clinch"),
        ("조지아주에서 낚시 면허가 필요해요?", "ko", "all-fish#rule-license-ga"),
        ("조지아주에서 크래피는 몇 마리까지 가져갈 수 있어요?", "ko", "all-fish#care-possession-ga"),
    ],
)
def test_japanese_and_korean_questions_find_the_passage(client, question, lang, expected):
    body = client.post("/api/ask", json={"question": question, "lang": lang}).json()
    assert body["answer_source"] == "passages", body
    assert expected in [c["id"] for c in body["citations"]]
    assert body["answer"] == replies.passages_intro(lang)


def test_japanese_and_korean_off_topic_questions_are_declined_in_their_language(client):
    body = client.post("/api/ask", json={"question": "カレーの作り方は？"}).json()
    assert body["trace"]["outcome"] == "off_topic", body
    assert body["answer"].startswith("釣りの質問ではないようです")
    body = client.post("/api/ask", json={"question": "김치찌개 만드는 방법"}).json()
    assert body["trace"]["outcome"] == "off_topic", body
    assert body["answer"].startswith("낚시 질문이 아닌 것 같아요")
