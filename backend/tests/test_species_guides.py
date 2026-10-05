"""Tests for the species guides (app/knowledge/species_guides.py) and
GET /api/species/guides.

Most of these are content-integrity checks: a guide is shown to beginners
as advice, so a setup without a source, a species the scraper can create
but has no guide for, or a forage fish with rod-and-reel setups would all
be real defects, not style issues.
"""
from app.data_import.tpwd_lake_survey_scraper import (
    KNOWN_SPECIES,
    PLACEHOLDER_PROFILE,
    upsert_species,
)
from app.knowledge.species_guides import DIET_TYPES, GUIDES, SOURCES, TPWD_LIMITS_URL, get_guide
from app.models.waterbody import Species


def test_every_species_the_scraper_can_create_has_a_guide():
    missing = [name for name in KNOWN_SPECIES if get_guide(name) is None]
    assert missing == []


def test_every_setup_cites_at_least_one_known_source():
    for guide in GUIDES:
        for setup in guide.setups:
            assert setup.source_ids, f"{guide.common_name}: {setup.name} has no source"
            assert all(i in SOURCES for i in setup.source_ids)
            # And the guide's own source list includes them, so the page's
            # source list is complete.
            assert set(setup.source_ids) <= set(guide.source_ids), (guide.common_name, setup.name)


def test_every_sport_fish_has_at_least_two_setups_and_a_bait():
    for guide in GUIDES:
        if guide.role == "sport":
            assert len(guide.setups) >= 2, guide.common_name
            assert guide.live_baits or guide.lures, guide.common_name
            assert guide.difficulty in {"beginner", "intermediate", "advanced"}


def test_every_guide_has_a_diet_type():
    for guide in GUIDES:
        assert guide.diet_type in DIET_TYPES, guide.common_name
    # Both bait fish are filter feeders; every sport fish here is a
    # predator of some kind (carnivore) except the catch-all-eater catfish.
    forage = {g.common_name: g.diet_type for g in GUIDES if g.role == "forage"}
    assert set(forage.values()) == {"filter_feeder"}


def test_every_setup_names_whether_its_lure_or_bait():
    """The page groups setups into a Lure-fishing and a Bait-fishing
    section (previously an undifferentiated numbered list), so every
    setup needs a method the frontend can group on."""
    for guide in GUIDES:
        for setup in guide.setups:
            assert setup.method in {"lure", "bait", "either"}, (guide.common_name, setup.name)


def test_forage_fish_have_no_rod_setups_and_say_how_to_get_them():
    forage = [g for g in GUIDES if g.role == "forage"]
    assert {g.common_name for g in forage} == {"Gizzard Shad", "Threadfin Shad"}
    for guide in forage:
        assert guide.setups == ()
        assert guide.how_to_get and guide.bait_for and guide.identification
        assert guide.difficulty is None


def test_no_guide_states_bag_or_length_limits():
    """Limits change and vary by lake: link to TPWD instead (PRD §4.7)."""
    banned = ("bag limit", "daily limit", "minimum length", "slot limit", "length limit", "size limit")
    for guide in GUIDES:
        text = " ".join(
            [guide.summary, guide.diet, *guide.where_and_when, *guide.tips, *guide.legal_notes]
        ).lower()
        assert not any(b in text for b in banned), guide.common_name


def test_list_endpoint_returns_every_guide_sport_fish_first(client):
    body = client.get("/api/species/guides").json()
    assert len(body) == len(GUIDES)
    roles = [g["role"] for g in body]
    assert roles == sorted(roles, key=lambda r: r != "sport")
    assert body[0]["difficulty"] == "beginner"
    assert all(g["limits_url"] == TPWD_LIMITS_URL for g in body)


def test_guide_endpoint_expands_setup_sources(client):
    body = client.get("/api/species/guides/largemouth-bass").json()
    assert body["common_name"] == "Largemouth Bass"
    assert body["scientific_name"] == "Micropterus salmoides"
    assert body["diet_type"] == "carnivore"
    first = body["setups"][0]
    assert first["sources"] and first["sources"][0]["url"].startswith("https://")
    assert first["method"] in {"lure", "bait", "either"}
    assert {s["kind"] for s in body["sources"]} <= {"agency", "publication", "guide"}


def test_guide_lookup_accepts_the_display_name_too(client):
    assert client.get("/api/species/guides/White Crappie").json()["slug"] == "white-crappie"


def test_unknown_guide_is_a_404(client):
    assert client.get("/api/species/guides/peacock-bass").status_code == 404


def test_upsert_species_fills_placeholders_from_the_guide(db_session):
    db_session.add(
        Species(
            common_name="Bluegill",
            scientific_name="",
            difficulty="intermediate",
            profile=PLACEHOLDER_PROFILE,
        )
    )
    db_session.flush()

    bluegill = upsert_species(db_session, "Bluegill")

    assert bluegill.scientific_name == "Lepomis macrochirus"
    assert bluegill.difficulty == "beginner"
    assert bluegill.profile == get_guide("Bluegill").summary


def test_upsert_species_never_overwrites_hand_set_values(db_session):
    db_session.add(
        Species(
            common_name="Largemouth Bass",
            scientific_name="Micropterus salmoides",
            difficulty="beginner",
            profile="hand-written profile",
        )
    )
    db_session.flush()

    bass = upsert_species(db_session, "Largemouth Bass")

    assert bass.profile == "hand-written profile"


def test_forage_fish_get_no_difficulty_rating(db_session):
    shad = upsert_species(db_session, "Gizzard Shad")
    assert shad.difficulty == "n/a"
    assert shad.scientific_name == "Dorosoma cepedianum"
