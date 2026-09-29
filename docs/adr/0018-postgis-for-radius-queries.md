# ADR 0018: PostGIS for the radius query, plain lat/lng for the viewport

## Status
Accepted — amends ADR 0001. That ADR deferred PostGIS and named the
condition for revisiting it ("would need to move into SQL (or add PostGIS)
before this scales past a few hundred waterbodies"); this is that revisit.
Its other decision — points, not shoreline polygons — still stands: nothing
here adds polygon geometry.

## Context

ADR 0010 added a statewide OSM lake layer, taking Texas from tens of
hand-curated lakes to thousands of rows. Extending that layer to the rest of
the country is the next step, so the question is which queries stop working
at a national row count — the map fires a viewport query every time it stops
moving, and a radius query whenever someone searches near a place.

The assumption going in was that both were about to break for the same
reason: a composite B-tree on `(latitude, longitude)` can only range-scan
its first column, so a viewport over Houston would have to walk every lake
in the country sharing Houston's latitude. **That assumption was wrong, and
measuring it is what this ADR is really about.**

A million synthetic waterbodies were generated across the United States,
clustered the way real ones are (Minnesota and Maine dense, Nevada nearly
empty — a uniform spread would flatter any spatial index), and the candidate
query shapes were run against the same rows.

| viewport | rows returned | lat/lng B-tree | PostGIS `geog &&` |
|---|---|---|---|
| city (~0.2°) | 159 | 1.0 ms | 1.6 ms |
| metro (~1°) | 2,606 | 2.9 ms | 3.9 ms |
| region (~7°) | 152,017 | 28 ms | 123 ms |
| lower 48 | 905,450 | 89 ms | 252 ms |

PostgreSQL takes *both* columns of the composite index as index conditions
and, for a count, never touches the heap. The B-tree was never the problem.

The radius query was, and badly. The portable shape can only pre-filter on a
latitude band and then run haversine in Python, so its cost grows with the
width of the country rather than the size of the circle:

| radius from Minneapolis | rows fetched → kept | time |
|---|---|---|
| 160 km, latitude band + Python | 249,858 → 33,832 | 4,823 ms |
| 160 km, `ST_DWithin` | 33,760 → 33,760 | 555 ms |
| 40 km, latitude band + Python | 249,858 → 2,152 | 1,001 ms |
| 40 km, `ST_DWithin` | 2,144 → 2,144 | 57 ms |

Note the shape of it: the band costs the same whether the circle is 40 km or
160 km, because the band is set by latitude alone. Tightening the search
makes the portable version no cheaper. That is the thing that does not
survive a national layer.

## Decision

Use PostGIS for the radius query. Answer the viewport query with the same
`latitude BETWEEN … AND longitude BETWEEN …` comparison on both databases.

`database_url` alone decides. SQLite stays the default and the documented
dev path with no new setup; pointing it at PostgreSQL turns on `ST_DWithin`
with no code change and no data migration.

`app/db/spatial.py` is the only module that knows there are two shapes. It
exposes `bbox_filter`, `radius_filter` and `radius_is_exact` — the last
telling the caller whether the Python haversine pass is still required.
`api/waterbodies.py` and `services/pins.py` call those and contain no
dialect-specific SQL.

On PostgreSQL, `ensure_spatial_schema` (run at startup beside
`Base.metadata.create_all`) adds the PostGIS extension, a
`geography(Point, 4326)` column `GENERATED ALWAYS AS (…) STORED` from
`longitude`/`latitude`, and a GiST index on it. All three exist for the
radius query alone.

`geography` rather than `geometry` so `ST_DWithin` takes plain metres and
stays correct over the curve of the earth without choosing a projection per
region of the country.

`latitude` and `longitude` remain the source of truth. Because `geog` is
GENERATED rather than written, no importer, seeder, test or schema learns
that PostGIS exists, and the column cannot drift out of sync — including for
rows written while the app ran on SQLite and later loaded into Postgres.

If the extension cannot be created — a provider that does not offer it, or a
role without rights — `ensure_spatial_schema` logs a warning, records that
PostGIS is unavailable, and the radius filter falls back to the band. Slower,
not wrong, and not a failure to boot.

`tests/conftest.py` takes `TEST_DATABASE_URL`, so the same suite runs against
SQLite or a real PostgreSQL database.

## Consequences

- The radius query is answered exactly, in the database, and its cost now
  tracks the size of the circle rather than the width of the map's coverage.
- The viewport query has one implementation instead of two. It is exact by
  construction — Leaflet's `toBBoxString()` rectangle has edges of constant
  latitude and longitude, which is precisely what the comparison expresses —
  and there is no second shape that can disagree with it.
- `ST_DWithin` and `haversine_km` do not agree to the last row: spheroid
  versus sphere puts lakes within a few tenths of a percent of the boundary
  on either side of it (72 of 33,832 at 160 km). Smaller than the error in
  plotting a lake at its centre point, and documented where it matters.
- Still points, not polygons. Shoreline work (PRD §4.4) is now a schema
  change rather than an infrastructure decision, since the extension and
  index are already there when the deployment provides them.
- Row counts, not query plans, were the next thing to face: a viewport over
  the lower 48 matches 905,450 rows, and the endpoint loaded all of them
  before applying `limit`, then kept the alphabetically first. ADR 0019
  fixes that (SQL limit, largest lakes kept); the zoom-out policy itself
  already lives in the frontend, which asks for verified lakes only below
  zoom 8.

## Alternatives considered

- **`geog && ST_MakeEnvelope(...)::geography` for the viewport.** This is
  what the first implementation shipped, and it was wrong. `&&` on geography
  compares *geodetic* bounding boxes, which PostGIS keeps as 3-D cartesian
  boxes; converting one back to a lat/lng rectangle neither contains nor is
  contained by it. On the data above it returned 9 lakes too many on a city
  viewport and 31,000 too many nationally, while in the same query dropping
  a dozen that were genuinely inside. It is a prefilter, not an answer, and
  not a sound prefilter either. `tests/test_spatial.py` now places lakes
  either side of a box edge; the original fixtures were hundreds of
  kilometres apart, which is exactly why they missed it.
- **A second GiST index on `(geog::geometry)` for the viewport.** Planar, so
  exact for points, and about twice as fast as the B-tree on a city viewport
  (0.5 ms vs 1.0 ms) — but 3 to 6 times slower on anything regional, and it
  buys a second index to maintain in exchange for half a millisecond on a
  query that is already a millisecond.
- **Require PostgreSQL + PostGIS everywhere.** One shape to test. Rejected
  for the reason ADR 0001 gave and that has not changed: it puts an
  extension install in front of anyone trying the project.
- **Write `geog` in application code rather than GENERATED.** Works on
  Postgres versions without generated columns. Rejected: every importer and
  test would have to remember to set it, and any that forgot would write
  rows invisible to the radius search while looking correct in the table.
