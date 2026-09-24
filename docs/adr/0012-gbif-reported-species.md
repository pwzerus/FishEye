# ADR 0012: GBIF species records as a "reported" tier

## Context

Of the 3,948 Texas lakes on the map (ADR 0010), only the 10 verified ones had
any fish data. The GBIF experiment
(`docs/experiments/2026-09-24-gbif-texas-coverage.md`) found GBIF records
for 469 lakes, including 49 of the 50 largest, agreeing with TPWD's survey
lists 84–90% of the time.

Presence records aren't the same as an official survey. One museum specimen
from 1967 is weak evidence of what's in a lake today, and a bounding box
catches records from the shore and from inflowing creeks. PRD constraints 1
and 10 forbid presenting unconfirmed species as confirmed.

## Decision

**A separate evidence tier, with its own table.** GBIF records go into
`species_occurrences`, one row per record, never into `waterbody_species`.
The UI calls this tier "reported" (on record, not verified), not
"community". That's because 62% of the records come from museum and
agency collections (Fishes of Texas), and "community" is reserved for
FishMate users' own reports later. `source` (`"gbif"` today) leaves room
for those.

| | Confirmed (`waterbody_species`) | Reported (`species_occurrences`) |
|---|---|---|
| Source | Official survey (TPWD) or hand curation | GBIF: museums, agencies, iNaturalist |
| Shown as | Species list with a confidence badge | "Recorded here": count, latest year, sources, link to the latest record |
| Scoring and the AI advisor | Yes | **No** |
| Map species filter | Yes | No |

Tests enforce the "No" column (`tests/test_gbif_import.py`): a record never
creates a `waterbody_species` row, the advisor's facts never contain a
reported-only species, and the map's species filter ignores records.

**Evidence strength is shown, not hidden.** Every reported species shows:
- its record count;
- the most recent year it was recorded;
- which groups recorded it: Fishes of Texas, iNaturalist, TPWD, or other
  museums and surveys;
- a link to the most recent record on gbif.org, so anyone can check it.

A single record from before 2000, or undated, is flagged "weak evidence"
rather than dropped: it is still the only information there is.

**Matching** reuses the experiment's code, now moved into
`app/data_import/gbif_occurrence_import.py` so the two can't drift apart:
- coordinates must be within 1 km uncertainty;
- fossils and non-guide species are dropped;
- a record goes to the smallest OSM lake bounding box that contains it.

An OSM element that is one of our verified lakes, including a second
element of the same lake that the lake list never stored, credits the
verified lake. The panel says that records near a lake can include its
shoreline and inflowing creeks.

**Licences stay per record.** `license` is one of CC0, CC BY, CC BY-NC or
other/unknown. Setting `GBIF_EXCLUDE_NONCOMMERCIAL=true` limits every query
to CC0 and CC BY without re-importing. It's off for the portfolio stage and
must be on before any commercial use (`docs/commercialization.md`).

**Re-importing replaces** all GBIF records for the state. Records GBIF has
since removed or moved disappear, and nothing is duplicated. When the OSM
import replaces an OSM-only lake with a verified one, the lake's records
move to the verified lake.

**Creating the new table.** The API creates missing tables at startup
(`create_all`, which never alters existing ones), so an existing dev
database needs no rebuild.

## Consequences

- 469 Texas lakes now say something about their fish. For the other ~3,500,
  the panel still says nothing is known.
- The map marks OSM lakes that have records, so a user can find them.
- Bounding-box matching over-credits large lakes with river arms. The fix is
  matching against lake outlines, which needs the OSM import to keep
  polygons (or PostGIS, ADR 0001). That's the next precision improvement.
- The importer runs on a machine that can reach api.gbif.org, like the OSM
  import. Other states need a bounding box in `STATE_BOUNDS` and their OSM
  layer first.
- For publication-grade citation, switch from the search API to the GBIF
  download API, which issues a DOI per download.
