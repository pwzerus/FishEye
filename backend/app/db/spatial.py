"""The map's "what is inside this box / near this point" filters, in the
two shapes this app's two databases can answer them.

WHY THIS EXISTS
---------------
The viewport query is the single hottest query in the app: the map fires one
every time it stops moving. On SQLite with a few thousand Texas lakes, a
plain `latitude BETWEEN … AND longitude BETWEEN …` against the composite
B-tree index is perfectly fine. It stops being fine at national scale.

A composite B-tree on (latitude, longitude) can only range-scan on its first
column: the latitude band narrows the scan, the longitude test is then
applied row by row to everything in that band. A viewport over Houston has
to walk every lake and pond in the United States that shares Houston's
latitude — Florida, Louisiana, northern Mexico's neighbours — to throw
almost all of them away. The radius query is worse: it pre-filters on
latitude alone and then computes haversine in *Python* over whatever came
back, so the work grows with the width of the country, not with the size of
the circle the person asked about.

PostGIS answers both from a GiST index over a real spatial type, where the
index understands two dimensions at once and the distance test happens in
the database.

THE SHAPE OF THE COMPROMISE
---------------------------
`latitude` / `longitude` remain the source of truth in both databases — they
are what every importer writes and what every schema returns. On PostgreSQL
the `geog` column is GENERATED from them (see `ensure_spatial_schema`), so:

- no importer, seeder or test has to know PostGIS exists;
- the column can never drift out of sync with the coordinates;
- switching `database_url` between SQLite and Postgres needs no data
  migration and no code change, only a re-import.

If PostGIS turns out to be unavailable on a Postgres database (a managed
provider that doesn't offer the extension, or a role without rights to
create it), every function here quietly falls back to the SQLite shape.
That is slower, not wrong.
"""
from __future__ import annotations

import logging

from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement, TextClause

from app.models.waterbody import Waterbody

logger = logging.getLogger(__name__)

# Answered once per engine by `ensure_spatial_schema`, then read by every
# request. None means "nobody has checked yet" (a test that builds its own
# engine, say), which the accessors treat as "no PostGIS".
_postgis_ready: dict[str, bool] = {}

# 1 degree of latitude is ~111 km anywhere; longitude degrees shrink towards
# the poles, so using the latitude figure for both makes the SQLite
# pre-filter box too wide rather than too narrow. Too wide only costs time
# (the haversine pass below removes the extras); too narrow would silently
# drop lakes that are genuinely in range.
KM_PER_DEGREE_LAT = 111.0

_SPATIAL_DDL = (
    "CREATE EXTENSION IF NOT EXISTS postgis",
    # GENERATED … STORED: Postgres recomputes this whenever latitude or
    # longitude changes, so lat/lng stay the only thing application code
    # writes. geography (not geometry) so that ST_DWithin takes plain metres
    # and is correct over the curve of the earth without picking a
    # projection for each part of the country.
    """
    ALTER TABLE waterbodies ADD COLUMN IF NOT EXISTS geog
        geography(Point, 4326)
        GENERATED ALWAYS AS (
            ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography
        ) STORED
    """,
    "CREATE INDEX IF NOT EXISTS ix_waterbodies_geog ON waterbodies USING GIST (geog)",
)


def ensure_spatial_schema(engine: Engine) -> bool:
    """Bring a PostgreSQL database up to the spatial schema, and record
    whether it worked so the query helpers know which shape to emit.

    Idempotent: every statement is IF NOT EXISTS, so this runs on every
    startup (there are no migrations in this project — see
    `Base.metadata.create_all` in main.py, which this mirrors).

    Returns True when PostGIS filters may be used. Always False on SQLite,
    which is not an error: that is the documented dev default.
    """
    if engine.dialect.name != "postgresql":
        _postgis_ready[_engine_key(engine)] = False
        return False

    try:
        with engine.begin() as conn:
            for statement in _SPATIAL_DDL:
                conn.execute(text(statement))
    except SQLAlchemyError as exc:
        # Most likely: the database role may not CREATE EXTENSION (common on
        # locked-down managed Postgres). The app still works — the lat/lng
        # filters below are the fallback — so this is a warning, not a crash
        # on boot.
        logger.warning(
            "PostGIS unavailable (%s). Falling back to latitude/longitude "
            "filtering, which is slower on a large waterbodies table.",
            exc.__class__.__name__,
        )
        _postgis_ready[_engine_key(engine)] = False
        return False

    logger.info("PostGIS spatial index ready on waterbodies.geog")
    _postgis_ready[_engine_key(engine)] = True
    return True


def _engine_key(engine: Engine) -> str:
    return str(engine.url)


def uses_postgis(db: Session) -> bool:
    """Whether this session's database can answer spatial filters itself."""
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return False
    return _postgis_ready.get(_engine_key(bind.engine), False)


def bbox_filter(
    db: Session, west: float, south: float, east: float, north: float
) -> ColumnElement[bool] | TextClause:
    """Lakes inside the map's visible rectangle."""
    if uses_postgis(db):
        # ST_MakeEnvelope builds the viewport rectangle; && is the bounding
        # box overlap operator, which is what the GiST index actually
        # answers. For point rows "bounding boxes overlap" and "the point is
        # inside the rectangle" are the same question, so this needs no
        # second, exact pass.
        return text(
            "waterbodies.geog && ST_MakeEnvelope(:west, :south, :east, :north, 4326)::geography"
        ).bindparams(west=west, south=south, east=east, north=north)

    return Waterbody.latitude.between(south, north) & Waterbody.longitude.between(west, east)


def radius_filter(
    db: Session, lat: float, lng: float, radius_km: float
) -> ColumnElement[bool] | TextClause:
    """Lakes within `radius_km` of a point.

    On PostGIS this is the whole answer. On SQLite it is only a bounding-box
    pre-filter and the caller must still run `refine_radius` — see
    `radius_is_exact`.
    """
    if uses_postgis(db):
        return text(
            "ST_DWithin(waterbodies.geog, "
            "ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :metres)"
        ).bindparams(lng=lng, lat=lat, metres=radius_km * 1000.0)

    pad = radius_km / KM_PER_DEGREE_LAT
    return Waterbody.latitude.between(lat - pad, lat + pad)


def radius_is_exact(db: Session) -> bool:
    """True when `radius_filter` already returned only rows in range, so the
    caller can skip the Python distance pass."""
    return uses_postgis(db)
