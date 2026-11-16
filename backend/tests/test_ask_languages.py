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
    # Spanish's little words ("la", "el", "un") are dropped (2026-11-16).
    assert es.to_english("¿Cómo pesco LOBINA NEGRA en la orilla?") == "how catch largemouth bass in bank shore"
    assert es.to_english("¿Cómo se arma un aparejo wacky?") == "how rig set up wacky rig"
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
    # Every passage now has its Spanish (ADR 0058): no "(en inglés)", no English quote.
    assert body["answer"] == replies.passages_intro_translated("es")
    assert all(c["lang"] == "es" for c in body["citations"])


def test_a_spanish_off_topic_question_is_declined_in_spanish(client):
    body = client.post("/api/ask", json={"question": "¿Cómo hago tacos de pollo?"}).json()
    assert body["answer_source"] == "no_match" and body["trace"]["outcome"] == "off_topic"
    assert body["answer"].startswith("Eso no parece una pregunta de pesca")


@pytest.mark.parametrize(
    ("question", "starts"),
    [("我家附近哪里能钓鱼？", "附近的钓点请在地图上查看"), ("附近有没有能钓鱼的湖", "附近的钓点请在地图上查看"), ("where can I fish near me", "For water near you")],
)
def test_where_can_i_fish_nearby_goes_to_the_map(client, question, starts):
    body = client.post("/api/ask", json={"question": question}).json()
    assert body["answer"].startswith(starts) and not body["citations"]


def test_a_question_about_a_place_nearby_is_not_sent_to_the_map(client):
    assert not client.post("/api/ask", json={"question": "水库附近可以夜钓吗"}).json()["answer"].startswith("附近的钓点请在地图上查看")


def test_an_english_question_on_the_chinese_site_is_introduced_in_chinese(client):
    body = client.post("/api/ask", json={"question": "what bait for crappie", "lang": "zh"}).json()
    assert body["answer_source"] == "passages"
    # Every passage it found has a Chinese version, so nothing is left to say about English.
    assert body["answer"] == replies.PASSAGES_INTRO_ZH_ORIGINAL
    assert body["citations"] and all(c["lang"] == "zh" for c in body["citations"])


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
    assert ja.to_english("Lake Lanierでバスは釣れる？") == "lake lanier bass catch fish"
    assert ko.to_english("블루길 바늘 크기는요?") == "bluegill hook size"
    # A stew isn't a bobber, and nothing Korean reaches the Chinese rules.
    assert ko.to_english("김치찌개 만드는 방법") == ""
    # 줄 is a line with its particles, not when it means to cut down or a jump rope.
    assert ko.to_english("초보자는 어떤 줄을 써야 해요?") == "beginner what line use"
    assert "line" not in ko.to_english("체중을 줄이려면 어떻게 해요?") + ko.to_english("줄넘기 잘하는 법")
    assert ja.to_english("ワッキーリグの作り方は？") == "wacky rig"


@pytest.mark.parametrize(
    ("question", "lang", "expected"),
    [
        # Found by asking the same questions in six languages (2026-11-16).
        ("¿Cómo se arma un aparejo wacky?", "es", "all-fish#rig-wacky"),
        ("¿Cómo armo un plomo corredizo con destorcedor?", "es", "all-fish#rig-bottom"),
        ("¿A qué hora del día es mejor pescar?", "es", "all-fish#timing-day"),
        ("ワッキーリグの作り方は？", "ja", "all-fish#rig-wacky"),
        ("魚が生きられるようにリリースするには？", "ja", "all-fish#care-release"),
        ("タル型サルカンは何のために使うの？", "ja", "all-fish#tackle-leaders"),
        ("와키 리그는 어떻게 만들어요?", "ko", "all-fish#rig-wacky"),
        ("물고기가 살 수 있게 놓아주려면 어떻게 해요?", "ko", "all-fish#care-release"),
        ("초보자는 어떤 줄을 써야 해요?", "ko", "all-fish#start-what-to-buy"),
    ],
)
def test_beginner_questions_in_other_languages_find_their_topic(client, question, lang, expected):
    # Keyword search only here (RAG_SEMANTIC=off): the live search, with the
    # embedding model, puts each of these first (F:/tmp/ask_verify, round 2).
    body = client.post("/api/ask", json={"question": question, "lang": lang}).json()
    assert body["answer_source"] == "passages", body
    assert expected in [c["id"] for c in body["citations"]]
    assert all(c["lang"] == lang for c in body["citations"])


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
    assert body["answer"] == replies.passages_intro_translated(lang)
    assert all(c["lang"] == lang for c in body["citations"])


def test_japanese_and_korean_off_topic_questions_are_declined_in_their_language(client):
    body = client.post("/api/ask", json={"question": "カレーの作り方は？"}).json()
    assert body["trace"]["outcome"] == "off_topic", body
    assert body["answer"].startswith("釣りの質問ではないようです")
    body = client.post("/api/ask", json={"question": "김치찌개 만드는 방법"}).json()
    assert body["trace"]["outcome"] == "off_topic", body
    assert body["answer"].startswith("낚시 질문이 아닌 것 같아요")


# "Why am I not catching anything", the beginner's commonest question, found
# the kids' page in English; in Spanish, Japanese and Korean it found "Bites,
# but nothing on the hook" first (2026-11-16, retriever._SKUNKED_RE).
@pytest.mark.parametrize(
    ("question", "lang"),
    [
        ("Why am I not catching anything?", "en"),
        ("Why isn't my kid catching anything?", "en"),
        ("The fish aren't biting today, what should I change?", "en"),
        ("Why am I not catching any bass?", "en"),
        ("¿Por qué no saco nada?", "es"),
        ("全然釣れないのはなぜ？", "ja"),
        ("왜 하나도 안 잡혀요?", "ko"),
    ],
)
def test_catching_nothing_finds_the_no_bites_topic_first(client, question, lang):
    body = client.post("/api/ask", json={"question": question, "lang": lang}).json()
    assert body["answer_source"] == "passages", body
    assert body["citations"][0]["id"] == "all-fish#trouble-no-bites"


@pytest.mark.parametrize(
    "question",
    [
        "I get bites but can't hook them",
        "Me pican pero no saco nada, ¿qué hago mal?",
        "アタリはあるのに釣れないのはなぜ？",
        "입질은 오는데 왜 안 잡혀요?",
    ],
)
def test_bites_and_nothing_hooked_is_the_other_topic(client, question):
    body = client.post("/api/ask", json={"question": question}).json()
    assert body["citations"][0]["id"] == "all-fish#trouble-stolen-bait", body


def test_what_counts_as_catching_nothing():
    from app.services.rag.retriever import AMBIGUOUS_ALIASES, asks_why_nothing_caught, caught_as_fish

    for said in ("Why am I not catching anything?", "I can't catch a thing", "Why don't I catch any crappie in summer?",
                 "No luck today", "They aren't biting", "Skunked again"):
        assert asks_why_nothing_caught(said), said
    # A rule, a bite named before "but", and plain how-to are not.
    for said in ("Can you not catch fish under 14 inches in Texas?", "I get bites but nothing on the hook",
                 "How do I catch more fish?"):
        assert not asks_why_nothing_caught(said), said
    bass = AMBIGUOUS_ALIASES["bass"]
    assert caught_as_fish("Why am I not catching any bass?", "bass", bass)
    assert not caught_as_fish("How do I turn the bass up?", "bass", bass)
    assert not caught_as_fish("Best strings to hook up a bass guitar", "bass", bass)


def test_korean_not_getting_stung_asks_how_to_hold(client):
    assert "hold" in ko.to_english("메기 가시에 안 찔리게 어떻게 잡아요?")
    body = client.post("/api/ask", json={"question": "메기 가시에 안 찔리게 어떻게 잡아요?"}).json()
    assert body["citations"][0]["id"] == "all-fish#safe-handling", body
