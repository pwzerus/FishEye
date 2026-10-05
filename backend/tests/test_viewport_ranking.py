"""What the map gets when a view holds more lakes than it can show.

At national scale one viewport can match hundreds of thousands of lakes. The
endpoint keeps the largest, never lets them displace a verified lake, and
does the cutting in SQL. See list_waterbodies in app/api/waterbodies.py.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.waterbody import State, Waterbody

NOW = datetime(2026, 9, 1, tzinfo=timezone.utc)
BOX = "-97.0,30.0,-96.0,31.0"


def _lake(state_id: int, name: str, i: int, *, tier: str = "osm", extent: float = 0.0) -> Waterbody:
    return Waterbody(
        state_id=state_id,
        name=name,
        latitude=30.5 + i * 0.01,
        longitude=-96.5,
        access_summary="",
        source_url="https://example.test",
        source_updated_at=NOW,
        data_tier=tier,
        osm_ref=None if tier == "verified" else f"way/{i}",
        extent_km2=extent,
    )


@pytest.fixture()
def crowded(db_session):
    """One verified lake and five OSM ones, named so that alphabetical order
    is the OPPOSITE of size order: the biggest lake sorts last by name."""
    tx = State(name="Texas", code="TX", official_source_url="https://tpwd.texas.gov/")
    db_session.add(tx)
    db_session.flush()
    db_session.add(_lake(tx.id, "Zed Verified Lake", 0, tier="verified"))
    for i, (name, km2) in enumerate(
        [("Ace Pond", 0.1), ("Bay Pond", 0.5), ("Cove Lake", 2.0), ("Dune Lake", 9.0), ("Elm Reservoir", 40.0)],
        start=1,
    ):
        db_session.add(_lake(tx.id, name, i, extent=km2))
    db_session.commit()
    return db_session


def _names(client, **params) -> list[str]:
    body = client.get("/api/waterbodies", params={"bbox": BOX, **params}).json()
    return [w["name"] for w in body]


def test_a_truncated_view_keeps_the_largest_lakes_not_the_alphabetically_first(client, crowded):
    # Room for the verified lake and two others. By name that would be Ace and
    # Bay, the two smallest ponds; by size it is Elm and Dune.
    assert _names(client, limit=3) == ["Zed Verified Lake", "Elm Reservoir", "Dune Lake"]


def test_a_verified_lake_is_never_displaced_by_a_bigger_osm_one(client, crowded):
    # Elm is 40 km² and the verified lake is 0, and the verified lake is still
    # the one kept when there is room for only one.
    assert _names(client, limit=1) == ["Zed Verified Lake"]


def test_an_untruncated_view_still_lists_everything_verified_first(client, crowded):
    names = _names(client)
    assert names[0] == "Zed Verified Lake"
    assert names[1:] == ["Elm Reservoir", "Dune Lake", "Cove Lake", "Bay Pond", "Ace Pond"]


def test_the_osm_tier_filter_ranks_by_size_too(client, crowded):
    assert _names(client, tier="osm", limit=2) == ["Elm Reservoir", "Dune Lake"]


def test_the_verified_tier_filter_returns_only_verified(client, crowded):
    assert _names(client, tier="verified") == ["Zed Verified Lake"]


def test_rows_from_before_the_column_existed_rank_last_rather_than_first(client, db_session):
    tx = State(name="Texas", code="TX", official_source_url="https://tpwd.texas.gov/")
    db_session.add(tx)
    db_session.flush()
    # extent_km2 is 0 for an OSM row imported before the column was added.
    db_session.add(_lake(tx.id, "Aaa Legacy Pond", 1, extent=0.0))
    db_session.add(_lake(tx.id, "Zzz Measured Lake", 2, extent=3.0))
    db_session.commit()

    assert _names(client, limit=1) == ["Zzz Measured Lake"]
