"""Baits and lures as linked terms (knowledge/bait_terms.py, api/baits.py)."""
from __future__ import annotations

from app.knowledge.angling_handbook import TOPICS
from app.knowledge.bait_terms import TERMS, fish_for


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
    crickets = {f.slug: f for f in fish_for(_term("insects"))}
    assert "bluegill" in crickets and "cricket" in crickets["bluegill"].why.lower()
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
    assert worms["title"] == "Worms and nightcrawlers" and worms["how"].startswith("How to hook")
    assert worms["sources"] and worms["sources"][0]["url"].startswith("https://")
    assert "蚯蚓" in worms["names"]["zh"]
    assert cards["cut-bait"]["skip_on"] == ["gizzard-shad", "threadfin-shad"]
