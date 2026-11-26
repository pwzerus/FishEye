"""The Chinese long text (app/knowledge/translations): every sentence translated,
no number lost on the way, and an unknown language simply stays English."""
import re

import pytest

from app.api.species import to_out
from app.knowledge import gear
from app.knowledge.angling_handbook import TOPICS
from app.knowledge.jurisdictions import JURISDICTIONS
from app.knowledge.species_guides import GUIDES
from app.knowledge.translations import Translator, table
from app.services.rag.chunking import build_passages
from app.services.rag.zh_search import ZhTopics

CJK = re.compile(r"[一-鿿]")
NUMBER = re.compile(r"\d+(?:\.\d+)?")


def _handbook() -> dict[str, str]:
    return {f"{t.id}#{i}": s for t in TOPICS for i, s in enumerate(t.body)}


def _gear() -> dict[str, str]:
    return {f"{i.id}.{part}": getattr(i, part) for i in gear.ITEMS for part in ("what", "tip")}


def _bait_rules() -> dict[str, str]:
    return {f"{j.code}#{i}": s for j in JURISDICTIONS.values() for i, s in enumerate(j.bait_rules)}


def _quick() -> dict[str, str]:
    from app.knowledge.handbook_quick import QUICK

    out = {}
    for topic, take in QUICK.items():
        out[f"{topic}.lead"] = take.lead
        out.update({f"{topic}.points#{i}": p for i, p in enumerate(take.points)})
    return out


TABLES = [("handbook", _handbook), ("gear", _gear), ("bait_rules", _bait_rules), ("quick", _quick)]


@pytest.mark.parametrize("name, english", TABLES)
def test_every_sentence_is_translated_and_none_is_left_over(name, english):
    assert set(table(name, "zh")) == set(english())


@pytest.mark.parametrize("name, english", TABLES)
def test_translations_are_chinese_and_keep_their_numbers(name, english):
    source = english()
    for key, zh in table(name, "zh").items():
        assert CJK.search(zh), key
        lost = set(NUMBER.findall(source[key])) - set(NUMBER.findall(zh))
        assert not lost, (key, lost)


def test_every_passage_ask_can_quote_has_its_chinese_version():
    assert [p.id for p in build_passages() if not p.text_zh] == []


@pytest.mark.parametrize(
    ("question", "topic"),
    [("中暑了怎么办", "safe-heat"), ("雷雨天钓鱼危险吗", "safe-lightning"), ("鱼身上有黑点", "care-black-spots")],
)
def test_a_chinese_question_finds_its_handbook_topic(question, topic):
    passages = build_passages()
    assert passages[ZhTopics(passages).rank(question)[0]].section == topic


def test_every_guide_is_fully_translated():
    for guide in GUIDES:
        assert to_out(guide, "zh").text_lang == "zh", guide.slug


def test_every_gear_item_comes_back_in_chinese(client):
    items = client.get("/api/gear?lang=zh").json()["items"]
    assert items and all(i["text_lang"] == "zh" and CJK.search(i["what"]) for i in items)


def test_every_handbook_topic_comes_back_in_chinese(client):
    topics = client.get("/api/species/handbook?lang=zh").json()
    assert topics and all(t["body_lang"] == "zh" and CJK.search(" ".join(t["body"])) for t in topics)


def test_bait_rules_come_back_in_chinese(client):
    states = client.get("/api/jurisdictions?lang=zh").json()
    with_rules = [s for s in states if s["bait_rules"]]
    assert with_rules and all(s["bait_rules_lang"] == "zh" and CJK.search(s["bait_rules"][0]) for s in with_rules)
    assert all(s["bait_rules_lang"] is None for s in client.get("/api/jurisdictions").json())


# Spanish, Japanese and Korean (ADR 0058): the same tables, plus the question library.
OTHER = ("es", "ja", "ko")
SCRIPT = {
    "es": re.compile(r"[a-záéíóúñü]", re.I),
    "ja": re.compile(r"[぀-ヿ]"),  # kana: kanji alone could be Chinese
    "ko": re.compile(r"[가-힣]"),
}


def _qa() -> dict[str, str]:
    from app.knowledge import angling_qa

    out = {f"categories.{c}": v["en"] for c, v in angling_qa.CATEGORIES.items()}
    for item in angling_qa.ITEMS:
        for part in ("question", "short", "body"):
            out[f"{item.id}.{part}"] = getattr(item, part)
    return out


@pytest.mark.parametrize("lang", OTHER)
@pytest.mark.parametrize("name, english", [*TABLES, ("qa", _qa)])
def test_every_sentence_has_its_spanish_japanese_and_korean(name, english, lang):
    assert set(table(name, lang)) == set(english())


@pytest.mark.parametrize("lang", OTHER)
@pytest.mark.parametrize("name, english", [*TABLES, ("qa", _qa)])
def test_other_languages_keep_their_numbers_and_are_not_english(name, english, lang):
    source = english()
    for key, text in table(name, lang).items():
        # A short Japanese label can be kanji alone (竿, a rod).
        assert SCRIPT[lang].search(text) or (lang == "ja" and len(text) <= 4 and CJK.search(text)), (key, text)
        lost = set(NUMBER.findall(source[key])) - set(NUMBER.findall(text))
        assert not lost, (key, lost)
        # A long sentence left in English would read as a half translation.
        assert len(source[key]) < 40 or text != source[key], key


@pytest.mark.parametrize("lang", OTHER)
def test_every_guide_is_fully_translated_in_other_languages(lang):
    assert [g.slug for g in GUIDES if to_out(g, lang).text_lang != lang] == []


@pytest.mark.parametrize("lang", OTHER)
def test_every_passage_ask_can_quote_has_its_other_languages(lang):
    # Only the text: a guide section's title is the page's own label, in Chinese too.
    assert [p.id for p in build_passages() if not p.text_in(lang)] == []


@pytest.mark.parametrize("lang", OTHER)
def test_every_page_of_long_text_comes_back_in_other_languages(client, lang):
    items = client.get("/api/gear", params={"lang": lang}).json()["items"]
    assert items and all(i["text_lang"] == lang for i in items)
    topics = client.get("/api/species/handbook", params={"lang": lang}).json()
    assert topics and all(t["body_lang"] == lang for t in topics)
    states = [s for s in client.get("/api/jurisdictions", params={"lang": lang}).json() if s["bait_rules"]]
    assert states and all(s["bait_rules_lang"] == lang for s in states)
    questions = client.get("/api/species/questions", params={"lang": lang}).json()
    assert questions and all(q["lang"] == lang and SCRIPT[lang].search(q["question"]) for q in questions)


@pytest.mark.parametrize("lang", ["en", "fr", "../../etc/passwd", ""])
def test_a_language_without_a_table_stays_english(client, lang):
    assert table("gear", lang) == {}
    words = Translator("gear", lang)
    assert words.text("hook-j.what", "A hook.") == "A hook."
    assert words.language is None
    body = client.get("/api/gear", params={"lang": lang}).json()
    assert body["items"][0]["what"] == gear.items()[0].what
    assert body["items"][0]["text_lang"] is None
