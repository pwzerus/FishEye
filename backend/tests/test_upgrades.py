"""A database built before extent_km2 existed has to keep working.

The project has no migration tool and create_all never alters a table that
already exists, so without app/db/upgrades.py anyone with a populated dev
database would hit "no such column: waterbodies.extent_km2" on their first map
request and have to delete it.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect, text

from app.db.session import Base
from app.db.upgrades import ensure_waterbody_ranking_schema

# The waterbodies table exactly as it was before this column: no extent_km2,
# and only the one composite index.
OLD_WATERBODIES = """
CREATE TABLE waterbodies (
    id INTEGER PRIMARY KEY,
    state_id INTEGER NOT NULL,
    name VARCHAR(128) NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    access_summary TEXT NOT NULL,
    source_url VARCHAR(512) NOT NULL,
    source_updated_at DATETIME NOT NULL,
    field_tested BOOLEAN NOT NULL,
    public_access_status VARCHAR(16) NOT NULL,
    data_tier VARCHAR(16) NOT NULL,
    osm_ref VARCHAR(32),
    water_type VARCHAR(16)
)
"""


@pytest.fixture()
def old_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        conn.execute(text(OLD_WATERBODIES))
        conn.execute(text("CREATE INDEX ix_waterbodies_lat_lng ON waterbodies (latitude, longitude)"))
        conn.execute(
            text(
                "INSERT INTO waterbodies (state_id, name, latitude, longitude, access_summary,"
                " source_url, source_updated_at, field_tested, public_access_status, data_tier)"
                " VALUES (1, 'Lake Fork', 32.8, -95.6, '', 'x', '2026-01-01', 0, 'open', 'verified')"
            )
        )
    yield engine
    engine.dispose()


def _index_names(engine) -> set[str]:
    return {i["name"] for i in inspect(engine).get_indexes("waterbodies")}


def test_an_old_database_gains_the_column_and_keeps_its_rows(old_engine):
    ensure_waterbody_ranking_schema(old_engine)

    with old_engine.connect() as conn:
        row = conn.execute(text("SELECT name, extent_km2 FROM waterbodies")).one()
    assert row.name == "Lake Fork"
    assert row.extent_km2 == 0  # existing rows are not lost and rank last


def test_an_old_database_gains_the_indexes(old_engine):
    ensure_waterbody_ranking_schema(old_engine)
    assert {
        "ix_waterbodies_verified_lat_lng",
        "ix_waterbodies_extent",
        "ix_waterbodies_state_id",
    } <= _index_names(old_engine)


def test_it_is_safe_to_run_on_every_startup(old_engine):
    ensure_waterbody_ranking_schema(old_engine)
    ensure_waterbody_ranking_schema(old_engine)  # must not raise or duplicate anything
    assert _index_names(old_engine).issuperset({"ix_waterbodies_extent"})


def test_an_upgraded_database_matches_a_fresh_one(old_engine, tmp_path):
    """The definitions in upgrades.py are a second copy of what the model
    declares. If they drift, old and new databases would behave differently
    for reasons nobody can see."""
    ensure_waterbody_ranking_schema(old_engine)

    import app.models  # noqa: F401  (register every model)

    fresh = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    Base.metadata.create_all(bind=fresh)
    try:
        assert _index_names(old_engine) == _index_names(fresh)
        old_cols = {c["name"] for c in inspect(old_engine).get_columns("waterbodies")}
        fresh_cols = {c["name"] for c in inspect(fresh).get_columns("waterbodies")}
        assert old_cols == fresh_cols
    finally:
        fresh.dispose()


def test_a_database_with_no_waterbodies_table_is_left_alone(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    try:
        ensure_waterbody_ranking_schema(engine)  # create_all has not run yet
        assert not inspect(engine).has_table("waterbodies")
    finally:
        engine.dispose()
