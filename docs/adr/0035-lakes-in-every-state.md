# ADR 0035: Lakes in every state, from Geofabrik extracts

## Status
Accepted. Extends ADR 0010 (statewide OSM layer) to all 50 states and DC.

## Context

The OpenStreetMap layer came from one Overpass query per state. Overpass is
a shared public service; the data-sourcing rules ask for bulk data from a
bulk channel. Geofabrik publishes a daily OpenStreetMap extract per state.

## Decision

- `geofabrik_lakes.py`: per state, download the extract once (resumable), read
  it with pyosmium in five filtered passes into the same payload shape the
  Overpass query returned, and hand that to `osm_waterbody_import.run`. The
  same tags, the same private-water rules, the same likely_private marks.
- Geofabrik's extracts carry a border buffer: water whose box doesn't reach
  the state (Census outlines the map already draws, with a 2 km margin) is
  dropped. Water on a border belongs to both states, as with Overpass.
- Alaska's outline runs west of -180 so the Aleutians stay one shape; lakes
  there are stored at their real longitudes (+172..+180). The state test,
  the API's viewport query and the map's markers handle the wrap.
- `osm_cache/progress.json` records finished states; a run resumes. The
  payloads (`osm_cache/<st>_osm.json`) are what a server imports, with no
  download and no pyosmium (`requirements-import.txt` is local-only).
- Every state gets a `states` row (agency home page as its source).

Checked on California against the earlier Overpass file: 2,895 lakes vs
2,886, the same filters skipping the same water.

## Results (local SQLite, 2026-10-26)

64,742 lakes in 51 states (Michigan 5,150, Wisconsin 4,338, Texas 3,987 …
DC 7); the SQLite file is 52 MB. Every state's extract took 0-21 s and its
import 0-4 s.

## Known gaps

- **Untyped water.** Like the Overpass query, only `natural=water` with
  `water=lake|reservoir|pond` (or `landuse=reservoir`) counts. Many lakes
  are tagged `natural=water` with a name and no `water=*`: in Minnesota
  7,422 such elements against 1,808 tagged `water=lake`. Including them
  would multiply some states' counts several times, and needs a name filter
  so river and bay polygons don't become lakes. Not done; a decision.
