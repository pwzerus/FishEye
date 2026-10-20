"""Tests for the statewide OpenStreetMap layer (osm_waterbody_import.py) and
the viewport query that serves it. Network-free: every test feeds a canned
Overpass-shaped payload.

The tests that matter most are the ones about what must NOT happen: a
private lake or ramp shown as public, an OSM entrance scored as confirmed
public access, a verified lake overwritten or duplicated.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sqlalchemy import select

from app.data_import import osm_waterbody_import as osm
from app.models.waterbody import AccessPoint, Waterbody, WaterbodySpecies
from app.services.recommendations import build_recommendations
from app.services.weather_adapter import CurrentConditions, WeatherSnapshot

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc)


def _lake(el_id, name, lat, lng, half_deg=0.02, **extra_tags):
    tags = {"natural": "water", "water": "reservoir", "name": name, **extra_tags}
    return {
        "type": "way",
        "id": el_id,
        "tags": tags,
        "center": {"lat": lat, "lon": lng},
        "bounds": {
            "minlat": lat - half_deg,
            "minlon": lng - half_deg,
            "maxlat": lat + half_deg,
            "maxlon": lng + half_deg,
        },
    }


def _ramp(el_id, lat, lng, **tags):
    return {"type": "node", "id": el_id, "lat": lat, "lon": lng, "tags": {"leisure": "slipway", **tags}}


# Lake Fork in conftest.seeded_lake is verified, centred at 32.8065, -95.5931.
PAYLOAD = {
    "elements": [
        # OSM's own copy of the verified lake, under a different word order.
        _lake(1, "Fork Lake", 32.80, -95.59, half_deg=0.1),
        # An OSM-only lake with a public ramp and a private ramp on it.
        _lake(2, "Lake Tawakoni", 32.85, -95.95),
        _ramp(101, 32.851, -95.951, name="Wind Point Park Ramp"),
        _ramp(102, 32.852, -95.952, access="private"),
        # A ramp on the verified lake: must not be attached to it.
        _ramp(103, 32.81, -95.60),
        # A ramp far from any lake (a river ramp): dropped.
        _ramp(104, 30.0, -97.0),
        # Filtered out before anything is written:
        _lake(3, "Tiny HOA Lake", 30.5, -97.5, half_deg=0.0005),
        _lake(4, "Private Ranch Lake", 31.0, -98.0, access="private"),
        # A named park pond (~150 m across): kept, as a pond.
        {**_lake(5, "Bee Creek Park Pond", 31.5, -98.5, half_deg=0.0005), "tags": {"natural": "water", "water": "pond", "name": "Bee Creek Park Pond"}},
        # A named pond on private land: dropped like any private lake.
        {**_lake(7, "Ranch Stock Tank", 31.7, -98.7), "tags": {"natural": "water", "water": "pond", "name": "Ranch Stock Tank", "access": "private"}},
        # A named fountain-sized pond: dropped.
        {**_lake(9, "Plaza Fountain Pond", 31.8, -98.8, half_deg=0.0001), "tags": {"natural": "water", "water": "pond", "name": "Plaza Fountain Pond"}},
        # An unnamed pond: dropped (the stock-tank case).
        {**_lake(10, "", 31.9, -98.9), "tags": {"natural": "water", "water": "pond"}},
        {**_lake(6, "", 31.6, -98.6), "tags": {"natural": "water", "water": "lake"}},
    ]
}


def _snapshot() -> WeatherSnapshot:
    return WeatherSnapshot(
        latitude=32.85,
        longitude=-95.95,
        current=CurrentConditions(
            temperature=72,
            temperature_unit="F",
            wind_speed="10 mph",
            wind_direction="SE",
            short_forecast="Sunny",
            is_daytime=True,
        ),
        hourly=[],
        alerts=[],
        source="nws",
        stale=False,
        fetched_at=NOW,
    )


# --- parsing / matching (pure) ---------------------------------------------


def test_parse_keeps_named_public_water_and_drops_private_tiny_and_unnamed():
    lakes, access, skipped = osm.parse_elements(PAYLOAD)
    kinds = {lake.name: lake.water_type for lake in lakes}
    assert kinds == {
        "Fork Lake": "reservoir",
        "Lake Tawakoni": "reservoir",
        "Bee Creek Park Pond": "pond",
    }
    assert skipped == {"too_small": 2, "private_lake": 2, "unnamed_lake": 2, "private_access": 1}
    assert {a.osm_ref for a in access} == {"node/101", "node/103", "node/104"}


def test_a_pond_under_the_lake_size_limit_is_kept_but_a_lake_that_size_is_not():
    """~150 m across: big enough for a pond, too small to be a real lake
    (a mislabelled decorative feature, more likely)."""
    pond = {**_lake(1, "Small Pond", 30.0, -97.0, half_deg=0.0005), "tags": {"natural": "water", "water": "pond", "name": "Small Pond"}}
    lake = _lake(2, "Small Lake", 30.0, -97.0, half_deg=0.0005)
    lakes, _, _ = osm.parse_elements({"elements": [pond, lake]})
    assert [x.name for x in lakes] == ["Small Pond"]


def test_access_goes_to_the_smallest_containing_lake_and_river_ramps_are_dropped():
    big = osm.OsmLake("way/1", "Big Reservoir", 30.0, -97.0, osm.Bounds(29.9, -97.1, 30.1, -96.9))
    cove = osm.OsmLake("way/2", "Cove Arm", 30.05, -97.05, osm.Bounds(30.04, -97.06, 30.06, -97.04))
    in_cove = osm.OsmAccess("node/1", None, 30.05, -97.05, "boat_ramp")
    in_big = osm.OsmAccess("node/2", None, 29.95, -96.95, "boat_ramp")
    nowhere = osm.OsmAccess("node/3", None, 35.0, -100.0, "boat_ramp")

    by_lake, unmatched = osm.assign_access_to_lakes([big, cove], [in_cove, in_big, nowhere])

    assert [a.osm_ref for a in by_lake["way/2"]] == ["node/1"]
    assert [a.osm_ref for a in by_lake["way/1"]] == ["node/2"]
    assert unmatched == 1


def test_core_name_ignores_word_order_of_lake_and_reservoir():
    assert osm.core_name("Lake Somerville") == osm.core_name("Somerville Lake")
    assert osm.core_name("Somerville Reservoir") == "somerville"
    assert osm.core_name("Lake Fork") != osm.core_name("Lake Conroe")


# --- upsert ------------------------------------------------------------------


def test_osm_lake_is_stored_as_unverified_with_unknown_access_and_no_species(db_session, seeded_lake):
    osm.run("TX", PAYLOAD, db_session)

    lake = db_session.scalar(select(Waterbody).where(Waterbody.name == "Lake Tawakoni"))
    assert lake is not None
    assert lake.data_tier == "osm"
    assert lake.public_access_status == "unknown"
    assert lake.source_url == "https://www.openstreetmap.org/way/2"
    assert db_session.scalars(
        select(WaterbodySpecies).where(WaterbodySpecies.waterbody_id == lake.id)
    ).all() == []


def test_osm_access_points_are_reported_never_confirmed_and_private_ones_are_absent(db_session, seeded_lake):
    osm.run("TX", PAYLOAD, db_session)

    lake = db_session.scalar(select(Waterbody).where(Waterbody.name == "Lake Tawakoni"))
    points = list(db_session.scalars(select(AccessPoint).where(AccessPoint.waterbody_id == lake.id)))
    assert [(p.name, p.public_status, p.access_type) for p in points] == [
        ("Wind Point Park Ramp", "osm_reported", "boat_ramp")
    ]


def test_osm_access_points_are_never_ranked_by_the_scoring_engine(db_session, seeded_lake):
    """The line between 'OpenStreetMap says there's a ramp' and 'this app
    recommends fishing here' — scoring only ever ranks confirmed_public."""
    osm.run("TX", PAYLOAD, db_session)
    lake = db_session.scalar(select(Waterbody).where(Waterbody.name == "Lake Tawakoni"))

    result = build_recommendations(db_session, lake.id, weather=_snapshot())

    assert result["candidates"] == []


def test_a_verified_lake_is_linked_not_duplicated_or_overwritten(db_session, seeded_lake):
    verified = seeded_lake["waterbody"]
    before = (verified.name, verified.latitude, verified.access_summary, verified.source_url)

    osm.run("TX", PAYLOAD, db_session)

    forks = list(db_session.scalars(select(Waterbody).where(Waterbody.name.in_(["Lake Fork", "Fork Lake"]))))
    assert [w.id for w in forks] == [verified.id]
    assert verified.data_tier == "verified"
    assert verified.osm_ref == "way/1"
    assert (verified.name, verified.latitude, verified.access_summary, verified.source_url) == before
    # The OSM ramp on the verified lake was not attached to it.
    statuses = {p.public_status for p in verified.access_points}
    assert statuses == {"confirmed_public"}


def test_import_is_idempotent(db_session, seeded_lake):
    osm.run("TX", PAYLOAD, db_session)
    counts = (
        len(db_session.scalars(select(Waterbody)).all()),
        len(db_session.scalars(select(AccessPoint)).all()),
    )

    second = osm.run("TX", PAYLOAD, db_session)

    assert (
        len(db_session.scalars(select(Waterbody)).all()),
        len(db_session.scalars(select(AccessPoint)).all()),
    ) == counts
    assert second.lakes_created == 0
    assert second.access_created == 0


def test_an_osm_lake_later_covered_by_a_verified_one_is_replaced(db_session, seeded_lake):
    osm.run("TX", PAYLOAD, db_session)
    tawakoni = db_session.scalar(select(Waterbody).where(Waterbody.name == "Lake Tawakoni"))
    # Simulate the TPWD scraper later adding Tawakoni as a verified lake under
    # a different spelling.
    db_session.add(
        Waterbody(
            state_id=seeded_lake["state"].id,
            name="Tawakoni Reservoir",
            latitude=32.85,
            longitude=-95.95,
            access_summary="verified",
            source_url="https://tpwd.texas.gov/tawakoni",
            source_updated_at=NOW,
        )
    )
    db_session.flush()
    tawakoni_id = tawakoni.id

    summary = osm.run("TX", PAYLOAD, db_session)

    assert summary.lakes_replaced_by_verified == 1
    assert db_session.get(Waterbody, tawakoni_id) is None
    remaining = list(db_session.scalars(select(Waterbody).where(Waterbody.name.like("%Tawakoni%"))))
    assert [(w.name, w.data_tier, w.osm_ref) for w in remaining] == [
        ("Tawakoni Reservoir", "verified", "way/2")
    ]
    assert db_session.scalars(
        select(AccessPoint).where(AccessPoint.public_status == "osm_reported", AccessPoint.waterbody_id == tawakoni_id)
    ).all() == []


# --- viewport query ------------------------------------------------------------


def test_bbox_returns_only_lakes_in_view_with_their_tier(client, db_session, seeded_lake):
    osm.run("TX", PAYLOAD, db_session)
    db_session.commit()

    # A box around Tawakoni only (west,south,east,north).
    resp = client.get("/api/waterbodies", params={"bbox": "-96.1,32.8,-95.9,32.9"})

    assert resp.status_code == 200
    assert [(w["name"], w["data_tier"]) for w in resp.json()] == [("Lake Tawakoni", "osm")]


def test_bbox_lists_verified_lakes_before_osm_ones(client, db_session, seeded_lake):
    osm.run("TX", PAYLOAD, db_session)
    db_session.commit()

    resp = client.get("/api/waterbodies", params={"bbox": "-100,25,-90,35"})

    tiers = [w["data_tier"] for w in resp.json()]
    assert tiers == sorted(tiers, key=lambda t: t != "verified")
    assert tiers[0] == "verified"


def test_malformed_bbox_is_a_422(client, seeded_lake):
    assert client.get("/api/waterbodies", params={"bbox": "not,a,box"}).status_code == 422
    assert client.get("/api/waterbodies", params={"bbox": "-95,33,-96,32"}).status_code == 422


def test_detail_exposes_the_tier(client, db_session, seeded_lake):
    osm.run("TX", PAYLOAD, db_session)
    db_session.commit()
    lake = db_session.scalar(select(Waterbody).where(Waterbody.name == "Lake Tawakoni"))

    body = client.get(f"/api/waterbodies/{lake.id}").json()

    assert body["data_tier"] == "osm"
    assert body["public_access_status"] == "unknown"
    assert body["species"] == []
    assert [p["public_status"] for p in body["access_points"]] == ["osm_reported"]


def test_advisor_never_calls_an_osm_source_official(db_session, seeded_lake):
    from app.services import ai_advisor

    osm.run("TX", PAYLOAD, db_session)
    lake = db_session.scalar(select(Waterbody).where(Waterbody.name == "Lake Tawakoni"))

    facts = ai_advisor.gather_facts(db_session, lake.id, weather=_snapshot())

    assert [s["label"] for s in facts["sources"]] == ["Lake Tawakoni — OpenStreetMap (community-mapped)"]


def test_a_lake_with_only_bounds_is_placed_at_their_midpoint():
    """The real Overpass response for lakes carries `bounds` and no
    `center` (see build_overpass_query)."""
    el = _lake(8, "Bounds Only Lake", 31.0, -97.0)
    del el["center"]
    lakes, _, _ = osm.parse_elements({"elements": [el]})
    assert (lakes[0].latitude, lakes[0].longitude) == (31.0, -97.0)


def test_query_asks_for_one_geometry_modifier_per_out_statement():
    q = osm.build_overpass_query("TX")
    assert '"ISO3166-2"="US-TX"' in q
    assert "out tags bb;" in q and "out tags center;" in q
    assert "center bb" not in q and "bb center" not in q


def test_a_pond_is_stored_as_a_pond_with_a_private_land_warning(client, db_session, seeded_lake):
    osm.run("TX", PAYLOAD, db_session)
    db_session.commit()
    pond = db_session.scalar(select(Waterbody).where(Waterbody.name == "Bee Creek Park Pond"))

    body = client.get(f"/api/waterbodies/{pond.id}").json()

    assert body["water_type"] == "pond"
    assert body["data_tier"] == "osm"
    assert body["public_access_status"] == "unknown"
    assert "private land" in body["access_summary"]


def test_verified_lakes_have_no_water_type(client, seeded_lake):
    items = client.get("/api/waterbodies").json()
    assert [(w["name"], w["water_type"]) for w in items] == [("Lake Fork", None)]


def test_an_official_name_with_a_qualifier_matches_its_common_osm_name(db_session, seeded_lake):
    """Real case from the first full Texas import: TPWD's "Fayette County
    Reservoir" is OSM's "Lake Fayette", and the exact-name rule missed it,
    leaving a duplicate unverified pin 2.3 km from the verified one."""
    db_session.add(
        Waterbody(
            state_id=seeded_lake["state"].id,
            name="Fayette County Reservoir",
            latitude=29.9127,
            longitude=-96.728,
            access_summary="verified",
            source_url="https://tpwd.texas.gov/fayette",
            source_updated_at=NOW,
        )
    )
    db_session.flush()
    fayette = {
        "type": "way",
        "id": 93668663,
        "tags": {"natural": "water", "water": "reservoir", "name": "Lake Fayette"},
        "bounds": {"minlat": 29.9126118, "minlon": -96.7539851, "maxlat": 29.9522301, "maxlon": -96.7126756},
    }

    summary = osm.run("TX", {"elements": [fayette]}, db_session)

    assert summary.lakes_created == 0
    rows = db_session.scalars(select(Waterbody).where(Waterbody.name.like("%Fayette%"))).all()
    assert [(w.name, w.data_tier, w.osm_ref) for w in rows] == [
        ("Fayette County Reservoir", "verified", "way/93668663")
    ]


def test_a_shared_word_alone_does_not_link_a_nearby_different_lake(db_session, seeded_lake):
    """A pond whose name contains 'Fork' next to Lake Fork, but whose own
    extent doesn't contain Lake Fork, stays a separate OSM entry."""
    pond = {
        "type": "way",
        "id": 555,
        "tags": {"natural": "water", "water": "pond", "name": "Fork Creek Pond"},
        "bounds": {"minlat": 32.70, "minlon": -95.70, "maxlat": 32.701, "maxlon": -95.699},
    }

    summary = osm.run("TX", {"elements": [pond]}, db_session)

    assert summary.lakes_created == 1
    assert seeded_lake["waterbody"].osm_ref is None


def test_rerunning_after_the_fix_removes_the_duplicate_already_in_the_db(db_session, seeded_lake):
    """What happens on the user's existing database: an OSM "Lake Fayette"
    row was created by the old matcher; re-running replaces it with the link."""
    verified = Waterbody(
        state_id=seeded_lake["state"].id,
        name="Fayette County Reservoir",
        latitude=29.9127,
        longitude=-96.728,
        access_summary="verified",
        source_url="https://tpwd.texas.gov/fayette",
        source_updated_at=NOW,
    )
    stale_osm = Waterbody(
        state_id=seeded_lake["state"].id,
        name="Lake Fayette",
        latitude=29.93,
        longitude=-96.73,
        access_summary="osm",
        source_url="https://www.openstreetmap.org/way/93668663",
        source_updated_at=NOW,
        data_tier="osm",
        public_access_status="unknown",
        osm_ref="way/93668663",
    )
    db_session.add_all([verified, stale_osm])
    db_session.flush()
    fayette = {
        "type": "way",
        "id": 93668663,
        "tags": {"natural": "water", "water": "reservoir", "name": "Lake Fayette"},
        "bounds": {"minlat": 29.9126118, "minlon": -96.7539851, "maxlat": 29.9522301, "maxlon": -96.7126756},
    }

    summary = osm.run("TX", {"elements": [fayette]}, db_session)

    assert summary.lakes_replaced_by_verified == 1
    assert db_session.scalar(select(Waterbody).where(Waterbody.name == "Lake Fayette")) is None
    assert verified.osm_ref == "way/93668663"



# --- one lake mapped as several elements (merge_pieces) ---------------------


def _rel(el_id, name, lat, lng, half_deg=0.02, **extra_tags):
    return {**_lake(el_id, name, lat, lng, half_deg, **extra_tags), "type": "relation"}


def _merged(payload_elements):
    elements, _, _ = osm.parse_elements({"elements": payload_elements})
    return {lake.osm_ref: lake for lake in osm.merge_pieces(elements)}


def test_a_way_and_a_relation_of_the_same_lake_become_one():
    lakes = _merged([
        _lake(1, "Amistad Reservoir", 29.49, -101.11, half_deg=0.01),  # a small piece
        _rel(2, "Amistad Reservoir", 29.6, -101.2, half_deg=0.2),  # the reservoir
    ])
    assert list(lakes) == ["relation/2"]
    amistad = lakes["relation/2"]
    assert amistad.extra_refs == ("way/1",)
    assert amistad.refs == ("relation/2", "way/1")
    # The biggest element decides the name and position; the box covers both.
    assert (amistad.latitude, amistad.longitude) == (29.6, -101.2)
    assert amistad.bounds.south == pytest.approx(29.4) and amistad.bounds.north == pytest.approx(29.8)


def test_the_same_wikidata_id_is_the_same_lake_whatever_its_names():
    lakes = _merged([
        _rel(1, "Presa Internacional Falcón", 26.8, -99.2, half_deg=0.2, wikidata="Q4967120"),
        _rel(2, "Falcon International Reservoir", 26.7, -99.25, half_deg=0.15, wikidata="Q4967120"),
    ])
    assert list(lakes) == ["relation/1"] and lakes["relation/1"].extra_refs == ("relation/2",)


def test_two_basins_of_one_reservoir_close_together_are_one_lake():
    # Twin Buttes: two sizeable basins about 1.8 km apart.
    lakes = _merged([
        _lake(1, "Twin Buttes Reservoir", 31.296, -100.496, half_deg=0.02),
        _rel(2, "Twin Buttes Reservoir", 31.363, -100.567, half_deg=0.035),
    ])
    assert list(lakes) == ["relation/2"]


def test_same_name_alone_does_not_merge():
    lakes = _merged([
        # Small same-named ponds a few hundred metres apart: different water.
        {**_lake(1, "playa", 34.0, -101.0, half_deg=0.001), "tags": {"natural": "water", "water": "pond", "name": "playa"}},
        {**_lake(2, "playa", 34.0, -101.006, half_deg=0.001), "tags": {"natural": "water", "water": "pond", "name": "playa"}},
        # Same name, big, but far apart: two different lakes.
        _lake(3, "Lake Graham", 33.16, -98.63, half_deg=0.04),
        _lake(4, "Graham Lake", 33.0, -98.715, half_deg=0.02),
        # Overlapping boxes but different names and no shared wikidata.
        _lake(5, "Lake Ray Hubbard", 32.85, -96.5, half_deg=0.05),
        _lake(6, "Rowlett Creek Cove", 32.88, -96.53, half_deg=0.02),
    ])
    assert sorted(lakes) == ["way/1", "way/2", "way/3", "way/4", "way/5", "way/6"]


def test_rows_from_an_earlier_unmerged_import_collapse_into_one(db_session, seeded_lake):
    from app.models.waterbody import SpeciesOccurrence

    state = seeded_lake["state"]
    pieces = [
        _rel(20, "Lake Meredith", 35.68, -101.6, half_deg=0.03),
        _rel(21, "Lake Meredith", 35.71, -101.57, half_deg=0.02),
        _ramp(201, 35.715, -101.565, name="Fritch Fortress Ramp"),
    ]
    # Before merging existed, each element became its own lake.
    elements, access, _ = osm.parse_elements({"elements": pieces})
    by_lake, _ = osm.assign_access_to_lakes(elements, access)
    osm.upsert(db_session, "TX", elements, by_lake, NOW)
    small = db_session.scalar(select(Waterbody).where(Waterbody.osm_ref == "relation/21"))
    db_session.add(SpeciesOccurrence(
        waterbody_id=small.id, species_name="Walleye", source="gbif", source_record_id="1",
        source_group="other", license="CC0", latitude=35.71, longitude=-101.57, imported_at=NOW,
    ))
    db_session.flush()
    assert len(db_session.scalars(select(Waterbody).where(Waterbody.name == "Lake Meredith")).all()) == 2

    summary = osm.run("TX", {"elements": pieces}, db_session)

    merediths = db_session.scalars(select(Waterbody).where(Waterbody.name == "Lake Meredith")).all()
    assert len(merediths) == 1
    meredith = merediths[0]
    assert meredith.osm_ref == "relation/20"
    assert summary.elements_merged == 1 and summary.pieces_merged == 1
    # The smaller piece's ramp and species record moved, not lost.
    assert [ap.name for ap in meredith.access_points] == ["Fritch Fortress Ramp"]
    assert [o.species_name for o in meredith.occurrences] == ["Walleye"]
    assert state.id == meredith.state_id

    again = osm.run("TX", {"elements": pieces}, db_session)
    assert (again.lakes_created, again.pieces_merged) == (0, 0)
    assert len(db_session.scalars(select(Waterbody).where(Waterbody.name == "Lake Meredith")).all()) == 1


def test_an_osm_piece_next_to_a_verified_piece_is_absorbed_into_it(db_session, seeded_lake):
    """The TPWD import verified one element of a lake; the OSM row for the
    lake's other element must go, not sit next to it as "unverified"."""
    pieces = [
        _rel(30, "Twin Buttes Reservoir", 31.363, -100.567, half_deg=0.035),
        _lake(31, "Twin Buttes Reservoir", 31.296, -100.496, half_deg=0.02),
    ]
    elements, access, _ = osm.parse_elements({"elements": pieces})
    osm.upsert(db_session, "TX", elements, {}, NOW)  # unmerged, as before
    verified = db_session.scalar(select(Waterbody).where(Waterbody.osm_ref == "way/31"))
    verified.data_tier = "verified"  # the TPWD import picked the smaller basin
    db_session.flush()

    osm.run("TX", {"elements": pieces}, db_session)

    rows = db_session.scalars(select(Waterbody).where(Waterbody.name == "Twin Buttes Reservoir")).all()
    assert [(w.osm_ref, w.data_tier) for w in rows] == [("way/31", "verified")]


# --- a second state (docs/adr/0028) ------------------------------------------

GA_PAYLOAD = {
    "elements": [
        _lake(201, "Lake Sidney Lanier", 34.20, -83.95, half_deg=0.15),
        _ramp(301, 34.21, -83.96, name="Little Ridge Park"),
    ]
}


def test_georgia_lakes_get_a_georgia_state_and_point_to_georgias_agency(client, db_session, seeded_lake):
    osm.run("GA", GA_PAYLOAD, db_session)
    db_session.commit()

    lake = db_session.scalar(select(Waterbody).where(Waterbody.name == "Lake Sidney Lanier"))
    assert lake.state.code == "GA" and lake.state.name == "Georgia"
    assert "Georgia Department of Natural Resources" in lake.access_summary
    assert "Texas" not in lake.access_summary
    assert [a.public_status for a in lake.access_points] == ["osm_reported"]

    states = {s["code"]: s for s in client.get("/api/states").json()}
    assert states["GA"]["has_waterbodies"] is True  # the map lights Georgia up
    assert states["GA"]["official_source_url"] == "https://georgiawildlife.com"


def test_texas_lakes_still_point_to_tpwd():
    assert "Texas Parks and Wildlife Department" in osm.osm_lake_summary("TX")


def test_a_state_without_an_agency_on_file_gets_a_generic_pointer():
    assert "Colorado's fish and wildlife agency" in osm.osm_lake_summary("CO")


# --- private water by name (docs/adr/0032) ----------------------------------


def _pond(el_id, name, lat, lng, **extra):
    return {**_lake(el_id, name, lat, lng), "tags": {"natural": "water", "water": "pond", "name": name, **extra}}


NAMED_PAYLOAD = {
    "elements": [
        _pond(401, "Private Pond", 33.10, -84.10),
        _pond(402, "Argo Lake (private)", 33.12, -84.12),
        _lake(403, "Pinetree Country Club Lake", 33.14, -84.14),
        _pond(404, "Rollins Ranch Lake", 33.16, -84.16),
        _pond(405, "Taylor Farm Park Pond", 33.18, -84.18),
        _pond(406, "County Farm Lake", 33.20, -84.20),
        _lake(407, "Lake Clubb", 33.22, -84.22),
        _ramp(501, 33.141, -84.141, name="Club ramp"),
    ]
}


def test_water_named_private_is_left_out_like_an_access_tag(db_session, seeded_lake):
    summary = osm.run("GA", NAMED_PAYLOAD, db_session)
    names = set(db_session.scalars(select(Waterbody.name)).all())
    assert "Private Pond" not in names and "Argo Lake (private)" not in names
    assert summary.skipped.get("private_by_name") == 2


def test_names_that_point_at_private_land_are_marked_likely_private(client, db_session, seeded_lake):
    summary = osm.run("GA", NAMED_PAYLOAD, db_session)
    db_session.commit()
    status = dict(db_session.execute(select(Waterbody.name, Waterbody.public_access_status)).all())
    assert status["Pinetree Country Club Lake"] == "likely_private"
    assert status["Rollins Ranch Lake"] == "likely_private"
    # A park, a county, and a word that merely contains "club" are not.
    assert status["Taylor Farm Park Pond"] == "unknown"
    assert status["County Farm Lake"] == "unknown"
    assert status["Lake Clubb"] == "unknown"
    assert summary.lakes_likely_private == 2
    lake = db_session.scalar(select(Waterbody).where(Waterbody.name == "Pinetree Country Club Lake"))
    assert client.get(f"/api/waterbodies/{lake.id}").json()["public_access_status"] == "likely_private"


def test_a_lake_stored_earlier_is_removed_once_it_is_marked_private(db_session, seeded_lake):
    before = {"elements": [_pond(601, "Hidden Pond", 33.3, -84.3), _ramp(701, 33.301, -84.301)]}
    osm.run("GA", before, db_session)
    db_session.commit()
    assert db_session.scalar(select(Waterbody).where(Waterbody.name == "Hidden Pond")) is not None

    # Someone tags it private on OSM; the next import must take it down,
    # with the entrance it had.
    after = {"elements": [_pond(601, "Hidden Pond", 33.3, -84.3, access="private"), _ramp(701, 33.301, -84.301)]}
    summary = osm.run("GA", after, db_session)
    db_session.commit()
    assert summary.lakes_removed_private == 1
    assert db_session.scalar(select(Waterbody).where(Waterbody.name == "Hidden Pond")) is None
    assert db_session.scalar(select(AccessPoint).where(AccessPoint.osm_ref == "node/701")) is None


def test_a_verified_lake_is_never_removed_by_an_osm_private_tag(db_session, seeded_lake):
    osm.run("TX", PAYLOAD, db_session)
    db_session.commit()
    tagged = {"elements": [{**_lake(1, "Fork Lake", 32.80, -95.59, half_deg=0.1), "tags": {
        "natural": "water", "water": "reservoir", "name": "Fork Lake", "access": "private"}}]}
    osm.run("TX", tagged, db_session)
    db_session.commit()
    assert db_session.scalar(select(Waterbody).where(Waterbody.data_tier == "verified")) is not None
