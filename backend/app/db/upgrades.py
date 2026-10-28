"""Additive schema changes for databases that were created before them.

This project has no migration tool (see `Base.metadata.create_all` in
main.py, and backend/README.md). `create_all` builds missing *tables* and
never touches an existing one — so a column or index added to a model
afterwards would exist for every fresh database and for none of the
developer's existing ones, which would then fail on the first query that
mentions it ("no such column"). Anyone with a populated dev database, or a
deployed one, would have to delete it.

Everything here is additive and idempotent, so it runs on every startup:
a column is added only when missing and every index is IF NOT EXISTS. It
never alters or drops anything. When a change needs more than that — a
type change, a backfill that cannot be a constant — this stops being the
right tool and it is time for a real migration tool.

The definitions must stay in step with app/models/waterbody.py, which is
what a fresh database gets. tests/test_upgrades.py builds the old shape by
hand and checks the two end up the same.
"""
from __future__ import annotations

import logging

from sqlalchemy import Engine, inspect, text

logger = logging.getLogger(__name__)

# Portable across SQLite and PostgreSQL: a constant DEFAULT lets both add a
# NOT NULL column to a table that already has rows.
_ADD_EXTENT = "ALTER TABLE waterbodies ADD COLUMN extent_km2 FLOAT NOT NULL DEFAULT 0"

# Nullable columns added since: (table, column, DDL type). Nothing to
# backfill; the importers that fill them say so when they run.
_NULLABLE_COLUMNS = (
    ("waterbodies", "dfg_water_id", "INTEGER"),
    ("waterbodies", "official_name", "VARCHAR(128)"),
    ("waterbodies", "public_land", "VARCHAR(16)"),
    ("waterbodies", "public_land_name", "VARCHAR(160)"),
    ("waterbodies", "public_land_manager", "VARCHAR(64)"),
    ("source_records", "source_key", "VARCHAR(64)"),
    ("source_records", "title", "VARCHAR(256)"),
    ("source_records", "licence_class", "VARCHAR(16)"),
    ("source_records", "licence_name", "VARCHAR(128)"),
    ("source_records", "citation", "TEXT"),
    # The photo check on catches (services/fish_id.py).
    ("catch_pins", "species_check", "VARCHAR(16)"),
    ("catch_pins", "species_check_confidence", "FLOAT"),
    ("catch_pins", "species_detected", "VARCHAR(64)"),
    ("catch_pins", "species_check_model", "VARCHAR(64)"),
    ("catch_pins", "species_check_photo_id", "INTEGER"),
    # Browsing catches by state and county (services/counties.py); startup
    # fills them for pins saved before (services/pins.fill_places).
    ("catch_pins", "state_code", "VARCHAR(2)"),
    ("catch_pins", "county_geoid", "VARCHAR(5)"),
    ("catch_pins", "county_name", "VARCHAR(64)"),
)

_INDEXES = (
    (
        "ix_waterbodies_state_id",
        "CREATE INDEX IF NOT EXISTS ix_waterbodies_state_id ON waterbodies (state_id)",
    ),
    (
        "ix_waterbodies_verified_lat_lng",
        "CREATE INDEX IF NOT EXISTS ix_waterbodies_verified_lat_lng "
        "ON waterbodies (latitude, longitude) WHERE data_tier = 'verified'",
    ),
    (
        "ix_waterbodies_extent",
        "CREATE INDEX IF NOT EXISTS ix_waterbodies_extent ON waterbodies (extent_km2 DESC)",
    ),
    (
        "ix_waterbodies_dfg_water_id",
        "CREATE INDEX IF NOT EXISTS ix_waterbodies_dfg_water_id ON waterbodies (dfg_water_id)",
    ),
)

# On tables other than waterbodies. A fresh database gets the same
# uniqueness from the model's unique=True.
_OTHER_INDEXES = (
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_source_records_source_key ON source_records (source_key)",
)
_PIN_PLACE_INDEX = "CREATE INDEX IF NOT EXISTS ix_catch_pins_place ON catch_pins (state_code, county_geoid)"


def ensure_waterbody_ranking_schema(engine: Engine) -> None:
    """Add `waterbodies.extent_km2` and the indexes the map's queries rely
    on (largest lakes in view, verified lakes in view, which states have
    lakes), if this database lacks them."""
    inspector = inspect(engine)
    if not inspector.has_table("waterbodies"):
        return  # create_all has not run; nothing to upgrade

    columns = {
        table: {c["name"] for c in inspector.get_columns(table)}
        for table in ("waterbodies", "source_records", "catch_pins")
        if inspector.has_table(table)
    }
    with engine.begin() as conn:
        if "extent_km2" not in columns["waterbodies"]:
            conn.execute(text(_ADD_EXTENT))
            logger.info(
                "Added waterbodies.extent_km2. Existing OpenStreetMap lakes rank "
                "last until the importer is re-run (it fills the column)."
            )
        for table, column, ddl_type in _NULLABLE_COLUMNS:
            if table in columns and column not in columns[table]:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
                logger.info("Added %s.%s.", table, column)
        for _name, ddl in _INDEXES:
            conn.execute(text(ddl))
        if "source_records" in columns:
            for ddl in _OTHER_INDEXES:
                conn.execute(text(ddl))
        if "catch_pins" in columns:
            conn.execute(text(_PIN_PLACE_INDEX))


def prepare_database(engine: Engine) -> None:
    """What the API does at startup, for command-line importers: build any
    missing table, then bring existing tables up to the current columns."""
    from app.db.session import Base
    import app.models  # noqa: F401  (registers every table on Base)

    Base.metadata.create_all(bind=engine)
    ensure_waterbody_ranking_schema(engine)
