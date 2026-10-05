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
)


def ensure_waterbody_ranking_schema(engine: Engine) -> None:
    """Add `waterbodies.extent_km2` and the indexes the map's queries rely
    on (largest lakes in view, verified lakes in view, which states have
    lakes), if this database lacks them."""
    inspector = inspect(engine)
    if not inspector.has_table("waterbodies"):
        return  # create_all has not run; nothing to upgrade

    columns = {c["name"] for c in inspector.get_columns("waterbodies")}
    with engine.begin() as conn:
        if "extent_km2" not in columns:
            conn.execute(text(_ADD_EXTENT))
            logger.info(
                "Added waterbodies.extent_km2. Existing OpenStreetMap lakes rank "
                "last until the importer is re-run (it fills the column)."
            )
        for _name, ddl in _INDEXES:
            conn.execute(text(ddl))
