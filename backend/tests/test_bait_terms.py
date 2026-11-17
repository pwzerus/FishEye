"""Baits and lures as linked terms (knowledge/bait_terms.py, api/baits.py)."""
from __future__ import annotations

from app.knowledge.angling_handbook import TOPICS
import re

import pytest

from app.knowledge.bait_terms import TERMS, card, fish_for


def _term(term_id):
    return next(t for t in TERMS if t.id == term_id)


def test_every_term_is_a_handbook_topic_and_named_in_all_five_languages():
    topics = {t.id for t in TOPICS}
    for t in TERMS:
        assert t.topic in topics, t.id
        assert set(t.names) == {"en", "zh", "es", "ko", "ja"}, t.id
    names = [n.lower() for t in TERMS for n in t.names["en"]]
    assert len(names) == len(set(names))  # one term per word


def test_a_term_links_the_fish_whose_guides_use_it_with_their_reason():
    crickets = {f["slug"]: f for f in card(_term("insects"))["fish"]}
    assert "bluegill" in crickets and "cricket" in crickets["bluegill"]["why"].lower()
    crayfish = {f.slug for f in fish_for(_term("crayfish"))}
    assert {"largemouth-bass", "smallmouth-bass"} <= crayfish


def test_a_plastic_worm_is_not_a_worm():
    from app.knowledge.bait_terms import _covered_by_longer, _english_re

    worms = _term("worms")
    assert not _english_re(worms).search(_covered_by_longer("Plastic worms and jigs", worms))
    assert _english_re(worms).search(_covered_by_longer("Nightcrawlers on the bottom", worms))


def test_the_api_serves_the_cards(client):
    resp = client.get("/api/baits")
    assert resp.status_code == 200 and "max-age" in resp.headers["cache-control"]
    cards = {c["id"]: c for c in resp.json()}
    assert len(cards) == len(TERMS)
    worms = cards["worms"]
    assert worms["title"] == "Worms and nightcrawlers" and worms["lang"] == "en"
    # The card has its own headings, so the sentence's label is gone.
    assert worms["how"].startswith("Run the hook") and worms["why"].startswith("Cheap")
    assert worms["sources"] and worms["sources"][0]["url"].startswith("https://")
    assert "蚯蚓" in worms["names"]["zh"]
    assert cards["cut-bait"]["skip_on"] == ["gizzard-shad", "threadfin-shad"]


@pytest.mark.parametrize("lang", ["zh", "es", "ja", "ko"])
def test_the_cards_come_back_whole_in_each_language(client, lang):
    """2026-11-16, the owner: a bait card on a Chinese fish page was English."""
    cards = client.get(f"/api/baits?lang={lang}").json()
    assert len(cards) == len(TERMS)
    for c in cards:
        assert c["lang"] == lang, c["id"]
        texts = [c["what"], c["why"], c["how"], *(f["why"] for f in c["fish"])]
        for text in filter(None, texts):
            # No English sentence left, and no label the heading already says.
            assert len(re.findall(r"\b(?:the|and|with|they|them|when|from)\b", text)) < 2, (c["id"], text)
            assert not re.match(r"^(?:Why|How to|When)\b", text), (c["id"], text)
            assert not text[0].islower(), (c["id"], text)
            assert not re.match(r"^(?:为什么|怎么|Por qué|Cómo|使う理由|効く理由|釣り方|付け方|쓰는 이유|다는 법|낚는 법)", text), (c["id"], text)


def test_traditional_chinese_cards(client):
    cards = {c["id"]: c for c in client.get("/api/baits?lang=zht").json()}
    assert cards["worms"]["lang"] == "zh-Hant"
    assert "蚯蚓" in cards["worms"]["what"] and "為" in "".join(c["what"] for c in cards.values())


def test_an_unknown_language_gets_english(client):
    cards = client.get("/api/baits?lang=../../etc").json()
    assert cards[0]["lang"] == "en"
