"""The map's viewport and radius filters, which have two implementations
(app/db/spatial.py: PostGIS where available, latitude/longitude ranges
otherwise) and must agree on every answer.

These run against whichever database TEST_DATABASE_URL names, so the same
assertions cover both shapes — that is the point. Run them once on SQLite
and once on Postgres before a deployment.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.db.spatial import bbox_filter, radius_filter, radius_is_exact, uses_postgis
from app.models.waterbody import State, Waterbody
from app.services.geo import haversine_km

NOW = datetime(2026, 9, 1, tzinfo=timezone.utc)

# Real coordinates, far enough apart that no assertion here turns on a
# rounding difference between the two implementations.
LAKES = {
    "Lake Travis": (30.4183, -97.9192),  # Austin
    "Lake Conroe": (30.4266, -95.6113),  # north of Houston, ~220 km from Austin
    "Lake Fork": (32.8065, -95.5931),  # north-east Texas
    "Lake Tahoe": (39.0968, -120.0324),  # California: never in a Texas answer
}
AUSTIN = (30.2672, -97.7431)


@pytest.fixture()
def lakes(db_session):
    tx = State(name="Texas", code="TX", official_source_url="https://tpwd.texas.gov/")
    db_session.add(tx)
    db_session.flush()
    for name, (lat, lng) in LAKES.items():
        db_session.add(
            Waterbody(
                state_id=tx.id,
                name=name,
                latitude=lat,
                longitude=lng,
                access_summary="",
                source_url="https://example.test",
                source_updated_at=NOW,
            )
        )
    db_session.commit()
    return db_session


def _names(db, clause) -> list[str]:
    return sorted(w.name for w in db.scalars(select(Waterbody).where(clause)).all())


def test_bbox_returns_only_what_is_inside_it(lakes):
    # A box over central Texas: Travis and Conroe are in it, the other two
    # are hundreds of km outside.
    inside = _names(lakes, bbox_filter(lakes, -98.5, 29.8, -95.0, 31.0))
    assert inside == ["Lake Conroe", "Lake Travis"]


def test_bbox_excludes_a_lake_that_shares_only_its_latitude(lakes):
    # Tahoe is at a different longitude entirely: the box must not be
    # decided on the latitude band alone.
    band = _names(lakes, bbox_filter(lakes, -98.5, 29.0, -95.0, 40.0))
    assert "Lake Tahoe" not in band


def test_bbox_is_exact_at_its_edges(db_session):
    """The fixtures above are hundreds of km apart, which is what let a
    wrong bbox implementation pass: it was out by thousandths of a degree.
    A viewport edge is where the two implementations have to agree, so put
    lakes just either side of one.

    (The implementation this caught answered with
    `geog && ST_MakeEnvelope(...)::geography`, whose geodetic bounding box
    is neither a superset nor a subset of the rectangle asked for.)
    """
    tx = State(name="Texas", code="TX", official_source_url="https://tpwd.texas.gov/")
    db_session.add(tx)
    db_session.flush()

    west, south, east, north = -97.0, 30.0, -96.0, 31.0
    nudge = 0.002  # ~200 m: far below the error that slipped through before
    placed = {
        "Just inside NE": (north - nudge, east - nudge),
        "Just inside SW": (south + nudge, west + nudge),
        "Just outside N": (north + nudge, (west + east) / 2),
        "Just outside S": (south - nudge, (west + east) / 2),
        "Just outside E": ((south + north) / 2, east + nudge),
        "Just outside W": ((south + north) / 2, west - nudge),
    }
    for name, (lat, lng) in placed.items():
        db_session.add(
            Waterbody(
                state_id=tx.id,
                name=name,
                latitude=lat,
                longitude=lng,
                access_summary="",
                source_url="https://example.test",
                source_updated_at=NOW,
            )
        )
    db_session.commit()

    assert _names(db_session, bbox_filter(db_session, west, south, east, north)) == [
        "Just inside NE",
        "Just inside SW",
    ]


def test_an_empty_corner_of_the_map_returns_nothing(lakes):
    assert _names(lakes, bbox_filter(lakes, -80.0, 24.0, -79.0, 25.0)) == []


def test_radius_agrees_with_haversine(lakes):
    lat, lng = AUSTIN
    radius_km = 250.0
    rows = lakes.scalars(select(Waterbody).where(radius_filter(lakes, lat, lng, radius_km))).all()
    if not radius_is_exact(lakes):
        # The SQLite path filters on a latitude band only, so it is allowed
        # to return extras — but never to miss one, which is what matters.
        rows = [w for w in rows if haversine_km(lat, lng, w.latitude, w.longitude) <= radius_km]

    expected = sorted(
        name for name, (la, ln) in LAKES.items() if haversine_km(lat, lng, la, ln) <= radius_km
    )
    assert sorted(w.name for w in rows) == expected
    assert "Lake Travis" in expected and "Lake Tahoe" not in expected


def test_the_sqlite_prefilter_never_drops_a_lake_in_range(lakes):
    """The latitude-band prefilter must be a superset of the true answer,
    or the haversine pass in the API would be filtering an already-wrong
    list. Only meaningful on the non-PostGIS path."""
    if uses_postgis(lakes):
        pytest.skip("PostGIS filters exactly; there is no prefilter to check")

    lat, lng = AUSTIN
    radius_km = 250.0
    prefiltered = {
        w.name for w in lakes.scalars(select(Waterbody).where(radius_filter(lakes, lat, lng, radius_km))).all()
    }
    truly_in_range = {
        name for name, (la, ln) in LAKES.items() if haversine_km(lat, lng, la, ln) <= radius_km
    }
    assert truly_in_range <= prefiltered


def test_the_endpoint_gives_the_same_answer_on_either_database(client, lakes):
    body = client.get("/api/waterbodies", params={"bbox": "-98.5,29.8,-95.0,31.0"}).json()
    assert sorted(w["name"] for w in body) == ["Lake Conroe", "Lake Travis"]

    near = client.get(
        "/api/waterbodies", params={"lat": AUSTIN[0], "lng": AUSTIN[1], "radius_km": 100}
    ).json()
    assert [w["name"] for w in near] == ["Lake Travis"]
