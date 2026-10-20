"""The angler's handbook (app/knowledge/angling_handbook.py), the guide
sections added with it, and GET /api/species/handbook (docs/adr/0024).

Content-integrity checks, like test_species_guides.py: a topic without a
source, a passage the Ask page can cite but the fish page doesn't show, or a
limit stated as a number would all be real defects."""
import re

from app.knowledge.angling_handbook import CATEGORIES, TOPICS
from app.knowledge.species_guides import GUIDES, SOURCES
from app.services.rag.chunking import SHARED_SLUG, build_passages


def test_every_topic_has_a_known_category_and_known_sources():
    assert len({t.id for t in TOPICS}) == len(TOPICS)
    for t in TOPICS:
        assert t.category in CATEGORIES, t.id
        assert t.source_ids, t.id
        assert all(i in SOURCES for i in t.source_ids), t.id
        assert t.body and all(sentence.strip() for sentence in t.body), t.id


def test_every_category_has_topics():
    assert {t.category for t in TOPICS} == set(CATEGORIES)


def test_every_topic_is_a_citable_passage_under_its_own_anchor():
    ids = {p.id for p in build_passages()}
    for t in TOPICS:
        assert f"{SHARED_SLUG}#{t.id}" in ids


def test_the_handbook_states_no_limit_as_a_number():
    """It may say that limits exist (the filleting rule needs to), never what
    they are: they change and vary by lake, so TPWD's page is the source."""
    numbered_limit = re.compile(r"\b\d+\s*(?:fish|per day|a day)\b|\b(?:bag|daily|creel) limit (?:is|of) \d", re.I)
    for t in TOPICS:
        assert not numbered_limit.search(" ".join(t.body)), t.id


def test_no_guide_section_added_by_the_expansion_states_a_limit():
    banned = ("bag limit", "daily limit", "minimum length", "slot limit", "length limit", "size limit")
    for guide in GUIDES:
        text = " ".join([*guide.habitat, *guide.habits, *guide.why_these_baits, *guide.eating]).lower()
        assert not any(b in text for b in banned), guide.common_name


def test_every_guide_has_habitat_habits_and_why_its_baits_work():
    for guide in GUIDES:
        assert guide.habitat, guide.common_name
        assert guide.habits, guide.common_name
        assert guide.why_these_baits, guide.common_name
        assert guide.identification, guide.common_name


def test_eighteen_guides_six_of_them_new():
    names = {g.common_name for g in GUIDES}
    assert len(GUIDES) == 19
    assert {
        "Flathead Catfish",
        "Guadalupe Bass",
        "Redear Sunfish",
        "Rainbow Trout",
        "Freshwater Drum",
        "Common Carp",
    } <= names


def test_handbook_endpoint_groups_topics_in_page_order_with_sources(client):
    body = client.get("/api/species/handbook").json()
    assert len(body) == len(TOPICS)
    order = list(CATEGORIES)
    seen = [order.index(t["category"]) for t in body]
    assert seen == sorted(seen)
    first = body[0]
    assert first["category_label"] == CATEGORIES[first["category"]]
    assert first["sources"] and first["sources"][0]["url"].startswith("https://")


def test_guide_endpoint_returns_the_new_sections(client):
    body = client.get("/api/species/guides/flathead-catfish").json()
    assert body["habitat"] and body["habits"] and body["why_these_baits"] and body["eating"]
    assert any("live" in reason for reason in body["why_these_baits"])
