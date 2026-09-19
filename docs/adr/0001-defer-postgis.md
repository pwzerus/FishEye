# ADR 0001: Defer PostGIS, use plain lat/lng for the MVP

## Status
Accepted (2026-09-19)

## Context
The PRD (§7, §8) specifies PostgreSQL + PostGIS so waterbody shoreline
polygons, access-point geometry, and later satellite-derived structure
data can be queried spatially (`ST_DWithin`, `ST_Contains`, etc.).

At MVP scope (3-10 hand-curated lakes, a handful of access points each,
no shoreline polygons or bathymetry yet), none of the actual data we have
is genuine polygon geometry — it's points (lake center, access point pins).
Requiring the `postgis/postgis` Docker image and the PostGIS extension adds
setup friction for anyone running the demo (a real risk against the
acceptance criterion: "招聘者可在 5 分钟内运行或体验核心流程" / a reviewer
should be running this in under 5 minutes), and it exercises a capability
(polygon geometry, spatial indexes) that nothing in the MVP scoring model
actually uses yet.

## Decision
Store `latitude`/`longitude` as plain `Float` columns on `Waterbody` and
`AccessPoint`. Distance filtering and future scoring signals that need
"how close" (not "what shape") use a Python haversine helper
(`app/services/geo.py`) at MVP data volumes (tens of lakes).

## Consequences
- Local dev and CI run against plain SQLite/Postgres with zero extension
  setup.
- Distance queries happen in application code, not the database. Fine at
  tens of rows; would need to move into SQL (or add PostGIS) before this
  scales past a few hundred waterbodies or before shoreline-shape features
  (PRD §4.4 "岸线形状识别岬角、湾口" / future satellite imagery work) land.
- Migrating to PostGIS later is additive: add geometry columns alongside
  the floats, backfill, cut over reads, drop the floats. Not a rewrite,
  because nothing else was built to depend on plain floats being the only
  representation (the schema module is the single seam).

## Alternatives considered
- **Ship PostGIS from day one**: matches the "real" target architecture
  more closely, but front-loads infrastructure complexity before there's
  any polygon data to justify it. Rejected for MVP; revisit when access
  points and shoreline shapes actually need to be queried spatially rather
  than by straight-line distance.
