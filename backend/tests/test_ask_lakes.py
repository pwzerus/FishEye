"""Ask's answers from the lake data (services/rag/lake_facts.py)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models.community import AskMiss
from app.models.waterbody import Species, State, Waterbody, WaterbodySpecies
from app.services import geocoding, place_suggest
from app.services.rag import lake_facts

WHEN = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _lake(db, state, name, *fish, status="open", tier="verified", at=(32.8, -95.6), extent=10.0):
    wb = Waterbody(
        state_id=state.id, name=name, latitude=at[0], longitude=at[1], access_summary="s",
        source_url="https://example.org", source_updated_at=WHEN, data_tier=tier,
        public_access_status=status, extent_km2=extent,
    )
    db.add(wb)
    db.flush()
    for sp in fish:
        db.add(WaterbodySpecies(
            waterbody_id=wb.id, species_id=sp.id, confidence="confirmed", evidence="e",
            source_url="https://example.org", observed_at=WHEN,
        ))
    db.flush()
    return wb


@pytest.fixture()
def lakes(db_session):
    tx = State(name="Texas", code="TX", official_source_url="https://x")
    ga = State(name="Georgia", code="GA", official_source_url="https://x")
    db_session.add_all([tx, ga])
    db_session.flush()
    bass = Species(common_name="Largemouth Bass", scientific_name="M", difficulty="beginner", profile="p")
    black = Species(common_name="Black Bullhead", scientific_name="A", difficulty="beginner", profile="p")
    db_session.add_all([bass, black])
    db_session.flush()
    _lake(db_session, tx, "Lake Travis", bass)
    _lake(db_session, ga, "Travis Lake", at=(33.0, -84.0))
    _lake(db_session, tx, "Lake Fork", bass, at=(32.8, -95.5))
    _lake(db_session, ga, "Lake Fork", at=(33.1, -84.1))
    _lake(db_session, tx, "Muddy Pond", black, at=(32.9, -95.5), extent=1.0)
    _lake(db_session, tx, "Closed Lake", bass, status="closed", at=(32.7, -95.6))
    _lake(db_session, tx, "Stone Lake;Other Name", tier="osm", at=(40.0, -80.0))
    db_session.commit()
    return db_session


@pytest.mark.parametrize(
    "question, name",
    [
        ("what fish are in Lake Travis", "Lake Travis"),
        ("Lake Travis crappie", "Lake Travis"),
        ("what bait works on travis lake?", "Travis Lake"),
    ],
)
def test_a_lake_named_in_a_question_is_found(lakes, question, name):
    found = lake_facts.answer(lakes, question, "TX", ())
    assert found is not None and found.kind == "lake"
    assert {found.lakes[0].name, *(o.name for o in found.same_name)} >= {name}


@pytest.mark.parametrize(
    "question",
    ["what's a good lake for beginners", "how do I fish a small lake", "the lake is muddy today", "best lure for bass in spring"],
)
def test_words_around_lake_are_not_a_lake(lakes, question):
    assert lake_facts.answer(lakes, question, "TX", ()) is None


def test_the_state_picked_comes_first_and_the_namesake_is_listed(lakes):
    found = lake_facts.answer(lakes, "Lake Fork", "GA", ())
    assert found.lakes[0].state_code == "GA"
    assert [o.state_code for o in found.same_name] == ["TX"]


def test_no_record_is_said_as_no_record(lakes):
    found = lake_facts.answer(lakes, "any walleye in Lake Travis", "TX", ("walleye", "largemouth-bass"))
    assert {a.slug: a.status for a in found.lakes[0].asked} == {"walleye": "no_record", "largemouth-bass": "on_record"}


def test_a_lake_with_no_fish_on_record_still_answers(client, lakes):
    body = client.post("/api/ask", json={"question": "what fish are in Stone Lake", "state": "TX"}).json()
    assert body["answer_source"] == "lakes" and body["citations"] == []
    assert body["lakes"]["lakes"][0]["name"] == "Stone Lake"  # OpenStreetMap's "A;B" names
    assert body["lakes"]["lakes"][0]["species"] == []
    assert lakes.scalars(select(AskMiss)).all() == []  # answered, so not a miss


def test_a_guide_question_on_a_lake_keeps_the_guide_passages(client, lakes):
    body = client.post("/api/ask", json={"question": "best bait for largemouth bass in Lake Travis"}).json()
    assert body["answer_source"] == "passages" and body["citations"]
    assert body["lakes"]["lakes"][0]["asked"][0]["status"] == "on_record"
    assert body["lakes"]["lakes"][0]["species"][0]["slug"] == "largemouth-bass"


def test_where_to_go_lists_open_lakes_for_the_fish_in_a_state(lakes):
    found = lake_facts.answer(lakes, "which lakes in Texas have largemouth bass", None, ("largemouth-bass",))
    assert found.kind == "list" and found.state == "TX"
    assert {w.name for w in found.lakes} == {"Lake Travis", "Lake Fork"}  # not the closed one


def test_a_guide_covers_every_fish_the_lake_data_files_under_it(lakes):
    found = lake_facts.answer(lakes, "where can I catch bullheads", "TX", ("brown-bullhead",))
    assert [w.name for w in found.lakes] == ["Muddy Pond"]
    assert found.lakes[0].species[0].slug == "brown-bullhead"


def test_where_to_go_near_a_place(lakes, monkeypatch):
    asked = []

    def geocode(q):
        asked.append(q)
        return geocoding.GeocodeResult(q, q, 32.8, -95.6)

    monkeypatch.setattr(geocoding, "geocode", geocode)
    found = lake_facts.answer(lakes, "where can I catch largemouth bass near Tyler", "TX", ("largemouth-bass",))
    assert asked == ["Tyler, TX"] and found.place == "Tyler"
    assert {w.name for w in found.lakes} == {"Lake Travis", "Lake Fork"}


def test_near_the_bottom_is_not_a_place(lakes, monkeypatch):
    def geocode(q):
        raise AssertionError(f"looked up {q!r}")

    monkeypatch.setattr(geocoding, "geocode", geocode)
    assert lake_facts.answer(lakes, "where do I catch bass near the bottom", None, ("largemouth-bass",)) is None


@pytest.fixture()
def places(monkeypatch):
    """FishEye's own place list, cut to a few (services/place_suggest.py);
    and no geocoder: a ZIP code or a town with its state never needs one."""
    index = place_suggest.PlaceIndex([
        place_suggest.Place("zip", "75701", "TX", 32.32, -95.30, 30_000, "Tyler"),
        place_suggest.Place("place", "Tyler", "TX", 32.35, -95.30, 105_000),
        place_suggest.Place("zip", "02467", "MA", 42.31, -71.15, 22_000, "Boston"),
    ])
    monkeypatch.setattr(place_suggest, "index", lambda: index)

    def geocode(q):
        raise AssertionError(f"looked up {q!r}")

    monkeypatch.setattr(geocoding, "geocode", geocode)


@pytest.mark.parametrize("question", ["75701 去哪里找鱼", "75701", "where can I fish near 75701", "Tyler, TX lakes", "Tyler, Texas fishing"])
def test_a_zip_code_or_a_town_with_its_state_is_a_place(lakes, places, question):
    found = lake_facts.answer(lakes, question, None, ())
    assert found.kind == "list" and found.place in ("75701 (Tyler, TX)", "Tyler, TX")
    assert found.place_latitude == pytest.approx(32.3, abs=0.1) and found.place_longitude == pytest.approx(-95.3)
    assert {w.name for w in found.lakes} == {"Lake Travis", "Lake Fork", "Muddy Pond"}  # within 80 km, open
    assert found.answers_it  # no fish asked about: the lakes and the map are the answer


def test_a_town_with_its_state_is_the_town_not_a_lake_of_its_name(lakes, places):
    tx = lakes.scalars(select(State).where(State.code == "TX")).one()
    bass = lakes.scalars(select(Species).where(Species.common_name == "Largemouth Bass")).one()
    _lake(lakes, tx, "Lake Tyler", bass, at=(32.2, -95.2))
    lakes.commit()
    near = lake_facts.answer(lakes, "where can I fish in Tyler, TX", None, ())
    assert near.kind == "list" and near.place == "Tyler, TX"
    assert "Lake Tyler" in {w.name for w in near.lakes}
    assert lake_facts.answer(lakes, "what fish are in Lake Tyler, TX", None, ()).kind == "lake"


def test_a_place_in_a_question_about_something_else_is_left_alone(lakes, places):
    assert lake_facts.answer(lakes, "do I need a license in Tyler, TX", None, ()) is None


def test_a_fish_asked_about_near_a_zip_code_keeps_the_guide_passages(lakes, places):
    found = lake_facts.answer(lakes, "where to catch bass near 75701", None, ("largemouth-bass",))
    assert {w.name for w in found.lakes} == {"Lake Travis", "Lake Fork"}
    assert not found.answers_it


def test_a_zip_code_with_no_lake_on_record_still_answers_with_the_map(client, lakes, places):
    body = client.post("/api/ask", json={"question": "02467 去哪里找鱼"}).json()
    assert body["answer_source"] == "lakes" and body["citations"] == []
    assert body["lakes"]["lakes"] == []
    assert body["lakes"]["place"] == "02467 (Boston, MA)"
    assert body["lakes"]["place_latitude"] == pytest.approx(42.31)


def test_a_place_that_cannot_be_looked_up_is_no_answer_not_an_error(lakes, monkeypatch):
    def geocode(q):
        raise geocoding.GeocodingUnavailable("down")

    monkeypatch.setattr(geocoding, "geocode", geocode)
    assert lake_facts.answer(lakes, "lakes near Tyler", None, ()) is None
