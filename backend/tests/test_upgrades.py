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


def test_an_old_database_gains_the_provenance_and_public_land_columns(old_engine):
    with old_engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE source_records (id INTEGER PRIMARY KEY, source_type VARCHAR(32) NOT NULL,"
            " url VARCHAR(512) NOT NULL, publisher VARCHAR(128) NOT NULL, retrieved_at DATETIME NOT NULL,"
            " valid_until DATETIME, checksum VARCHAR(64))"
        ))
    ensure_waterbody_ranking_schema(old_engine)
    ensure_waterbody_ranking_schema(old_engine)  # idempotent
    inspector = inspect(old_engine)
    wb_cols = {c["name"] for c in inspector.get_columns("waterbodies")}
    assert {"dfg_water_id", "official_name", "public_land", "public_land_name", "public_land_manager"} <= wb_cols
    src_cols = {c["name"] for c in inspector.get_columns("source_records")}
    assert {"source_key", "title", "licence_class", "licence_name", "citation"} <= src_cols
    assert "ix_waterbodies_dfg_water_id" in _index_names(old_engine)


def test_an_old_database_gains_the_photo_check_columns_and_keeps_its_pins(old_engine):
    # catch_pins as it was before the photo check (ADR 0037).
    with old_engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE catch_pins (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, latitude FLOAT NOT NULL,"
            " longitude FLOAT NOT NULL, title VARCHAR(80) NOT NULL, note TEXT, species_slug VARCHAR(64),"
            " species_other VARCHAR(60), caught_on DATE, visibility VARCHAR(16) NOT NULL, status VARCHAR(16) NOT NULL,"
            " status_reason VARCHAR(32), waterbody_id INTEGER, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)"
        ))
        conn.execute(text(
            "INSERT INTO catch_pins (user_id, latitude, longitude, title, visibility, status, created_at, updated_at)"
            " VALUES (1, 32.8, -95.6, 'Old pin', 'public', 'published', '2026-01-01', '2026-01-01')"
        ))
    ensure_waterbody_ranking_schema(old_engine)
    ensure_waterbody_ranking_schema(old_engine)  # idempotent
    cols = {c["name"] for c in inspect(old_engine).get_columns("catch_pins")}
    assert {"species_check", "species_check_confidence", "species_detected", "species_check_model", "species_check_photo_id"} <= cols
    # And where others see it (ADR 0038): an old pin's spot isn't shared.
    assert {"share_exact", "public_latitude", "public_longitude", "public_place"} <= cols
    with old_engine.connect() as conn:
        assert conn.execute(text("SELECT title, species_check FROM catch_pins")).one() == ("Old pin", None)
        assert conn.execute(text("SELECT share_exact, public_place FROM catch_pins")).one() == (0, None)
    assert "ix_catch_pins_public_lat_lng" in {i["name"] for i in inspect(old_engine).get_indexes("catch_pins")}
