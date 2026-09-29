"""The map's "what is inside this box / near this point" filters, in the
shapes this app's two databases can answer them.

WHAT IS AND IS NOT WORTH A SPATIAL INDEX
----------------------------------------
Measured on a million synthetic waterbodies spread over the United States,
clustered the way real lakes are (see docs/adr/0018):

The *radius* query is where PostGIS earns its place. The portable shape can
only pre-filter on a latitude band and then compute haversine in Python, so
the work grows with the width of the country rather than the size of the
circle: 250,000 rows dragged through the ORM to keep 34,000, about 4.8
seconds. `ST_DWithin` over a GiST index answers the same question in the
database, exactly, in about 0.7 — and unlike the band, it stays flat as the
map's coverage grows.

The *viewport* query turned out not to need it. The expectation was that a
composite B-tree on (latitude, longitude) could only range-scan its first
column and would have to walk every lake in the country sharing the
viewport's latitude. PostgreSQL does better than that: it takes both columns
as index conditions and, for a count, never touches the heap at all. A city
viewport is about a millisecond, and the PostGIS alternatives were slower on
every viewport bigger than a metro area — 3 to 6 times slower on a region.

So the bbox filter is the same lat/lng comparison on both databases. That is
not a compromise: it is exact by construction, it is what the frontend
actually asked for (Leaflet's `toBBoxString()` rectangle has edges of
constant latitude and longitude), and having one shape instead of two is one
less thing that can silently disagree.

A WARNING, PAID FOR
-------------------
The first version of this module answered the bbox with
`geog && ST_MakeEnvelope(...)::geography`. That is wrong, and quietly:
`&&` on geography compares *geodetic* bounding boxes, which PostGIS keeps as
3-D cartesian boxes. Converting one back to a lat/lng rectangle neither
contains nor is contained by it. On the data above it returned 9 lakes too
many on a city viewport, 31,000 too many nationally, and — in the same
query — dropped a dozen that were genuinely inside. It is a prefilter, never
an answer, and it is not even a sound prefilter. The tests missed it because
their fixtures were hundreds of kilometres apart, so nothing sat near an
edge; `test_spatial.py` now puts lakes either side of one.

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

# All of this exists for `radius_filter` alone — the bbox filter is served by
# the ordinary (latitude, longitude) index on the model.
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
) -> ColumnElement[bool]:
    """Lakes inside the map's visible rectangle.

    One shape for both databases, deliberately. The rectangle is Leaflet's
    `toBBoxString()`, whose edges are lines of constant latitude and
    longitude, so this comparison *is* the question rather than an
    approximation of it — and PostgreSQL answers it from
    ix_waterbodies_lat_lng using both columns. The module docstring has the
    measurements, and the reason the PostGIS form was removed.
    """
    return Waterbody.latitude.between(south, north) & Waterbody.longitude.between(west, east)


def radius_filter(
    db: Session, lat: float, lng: float, radius_km: float
) -> ColumnElement[bool] | TextClause:
    """Lakes within `radius_km` of a point.

    On PostGIS this is the whole answer, and an exact one. Otherwise it is
    only a latitude-band pre-filter and the caller must still drop the
    extras with `haversine_km` — ask `radius_is_exact` which case you are in.

    The two do not agree to the last row: `ST_DWithin` on geography measures
    on the spheroid, `haversine_km` on a sphere, so lakes sitting within a
    few tenths of a percent of the boundary can fall either side of it
    (measured at a million rows: 72 lakes of 33,832 at 160 km, 8 of 2,152 at
    40 km). That is a smaller error than plotting a lake at its centre point
    in the first place.
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
