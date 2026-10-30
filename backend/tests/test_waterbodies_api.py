def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_states(client, seeded_lake):
    r = client.get("/api/states")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["code"] == "TX"


def test_list_waterbodies_filters_by_state(client, seeded_lake):
    r = client.get("/api/waterbodies", params={"state_code": "TX"})
    assert r.status_code == 200
    assert len(r.json()) == 1

    r_empty = client.get("/api/waterbodies", params={"state_code": "CA"})
    assert r_empty.status_code == 200
    assert r_empty.json() == []


def test_list_waterbodies_filters_by_species(client, seeded_lake):
    r = client.get("/api/waterbodies", params={"species": "Largemouth Bass"})
    assert r.status_code == 200
    assert len(r.json()) == 1

    r_none = client.get("/api/waterbodies", params={"species": "Walleye"})
    assert r_none.status_code == 200
    assert r_none.json() == []


def test_list_waterbodies_filters_by_distance(client, seeded_lake):
    # Near Lake Fork (within radius)
    r_near = client.get(
        "/api/waterbodies",
        params={"lat": 32.80, "lng": -95.59, "radius_km": 50},
    )
    assert len(r_near.json()) == 1

    # Far away (Los Angeles) — should be excluded
    r_far = client.get(
        "/api/waterbodies",
        params={"lat": 34.05, "lng": -118.24, "radius_km": 50},
    )
    assert r_far.json() == []


def test_waterbody_detail_includes_access_points_and_species(client, seeded_lake):
    wb_id = seeded_lake["waterbody"].id
    r = client.get(f"/api/waterbodies/{wb_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Lake Fork"
    assert body["state_code"] == "TX"  # whose rules the panel shows
    assert len(body["access_points"]) == 1
    assert body["access_points"][0]["public_status"] == "confirmed_public"
    assert len(body["species"]) == 1
    assert body["species"][0]["confidence"] == "confirmed"


def test_waterbody_detail_404_for_missing_lake(client, seeded_lake):
    r = client.get("/api/waterbodies/999999")
    assert r.status_code == 404


def test_waterbody_species_endpoint_returns_conditions_shape(client, seeded_lake):
    wb_id = seeded_lake["waterbody"].id
    r = client.get(f"/api/waterbodies/{wb_id}/species")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["common_name"] == "Largemouth Bass"
    assert body[0]["conditions"] == []  # none added in this fixture


def test_states_say_which_ones_have_lakes(client, db_session, seeded_lake):
    # A State row with no lakes behind it (an import that found nothing) must
    # not light up as covered on the national map.
    from app.models.waterbody import State

    db_session.add(State(name="Oklahoma", code="OK", official_source_url="https://example.test"))
    db_session.commit()

    body = {s["code"]: s["has_waterbodies"] for s in client.get("/api/states").json()}
    assert body == {"OK": False, "TX": True}


def _lake(db, state, name, *, tier="osm", km2=0.1, at=(33.9, -84.1)):
    from datetime import datetime, timezone

    from app.models.waterbody import Waterbody

    wb = Waterbody(
        state_id=state.id, name=name, latitude=at[0], longitude=at[1], access_summary="",
        source_url="https://www.openstreetmap.org/way/1", data_tier=tier, extent_km2=km2,
        source_updated_at=datetime(2026, 9, 1, tzinfo=timezone.utc), field_tested=False,
    )
    db.add(wb)
    db.flush()
    return wb


def test_lake_search_puts_the_state_being_looked_at_first(client, db_session):
    """The 2026-10-29 walkthrough: "Freeman Lake" went to Kentucky's for
    someone looking at Georgia, with no choice offered."""
    from app.models.waterbody import State

    ga = State(name="Georgia", code="GA", official_source_url="https://georgiawildlife.com")
    ky = State(name="Kentucky", code="KY", official_source_url="https://fw.ky.gov")
    db_session.add_all([ga, ky])
    db_session.flush()
    _lake(db_session, ky, "Freeman Lake", km2=0.6)
    _lake(db_session, ga, "Freeman Lake", km2=0.1)
    _lake(db_session, ga, "Freeman Lake Estates Pond")
    _lake(db_session, ga, "Lake Lanier", tier="verified", km2=150)
    db_session.commit()

    found = client.get("/api/waterbodies/search", params={"q": "freeman lake", "state_code": "GA"}).json()
    assert [(m["name"], m["state_code"]) for m in found] == [
        ("Freeman Lake", "GA"), ("Freeman Lake", "KY"), ("Freeman Lake Estates Pond", "GA"),
    ]
    assert found[1]["state_name"] == "Kentucky"
    # With no state given, the bigger one leads; words in any order, any case.
    assert client.get("/api/waterbodies/search", params={"q": "Lake Freeman"}).json()[0]["state_code"] == "KY"
    assert client.get("/api/waterbodies/search", params={"q": "lanier"}).json()[0]["name"] == "Lake Lanier"
    assert client.get("/api/waterbodies/search", params={"q": "Atlanta"}).json() == []


def test_lake_search_tells_apart_lakes_sharing_a_name_in_one_state(client, db_session):
    """Georgia has four Freeman Lakes: the one nearest the map comes first,
    and each says which county it is in."""
    from app.models.waterbody import State

    ga = State(name="Georgia", code="GA", official_source_url="https://georgiawildlife.com")
    db_session.add(ga)
    db_session.flush()
    _lake(db_session, ga, "Freeman Lake", km2=0.5, at=(31.2, -83.5))  # south Georgia
    _lake(db_session, ga, "Freeman Lake", km2=0.1, at=(33.9197, -84.1438))  # Gwinnett
    db_session.commit()

    params = {"q": "Freeman Lake", "state_code": "GA", "lat": 33.91, "lng": -84.14}
    found = client.get("/api/waterbodies/search", params=params).json()
    assert [m["latitude"] for m in found] == [33.9197, 31.2]
    assert found[0]["county"] == "Gwinnett County"
