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
