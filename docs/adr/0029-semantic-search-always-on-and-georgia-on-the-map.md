# ADR 0029: Semantic search always on; Georgia on the map

## Status
Accepted. Changes ADR 0025's default; extends ADR 0010 (statewide OSM
layer) and ADR 0012 (GBIF records) to a second state.

## 1. Semantic search is no longer optional

ADR 0025 made the embedding model optional (`RAG_SEMANTIC=auto`): with it
missing, Ask fell back to keyword search without saying so. That fallback
was a development convenience, and it had become the weaker product hiding
behind a setting. Measured on the same questions (ADR 0028's run):

| | keyword only | keyword + semantic |
|---|---|---|
| paraphrases | 60% | 73% |
| rephrased, written after tuning | 77% | 90% |
| newest topics | 88% | 100% |
| fish names that are also everyday words | 94% | 100% |

The model costs 118 MB on disk, about 450 MB of memory and ~3 ms a question,
which the 2 GB server has room for. So:

- `RAG_SEMANTIC` defaults to `on`. The API loads Ask's search at startup and
  **refuses to start** without the model, with the two commands that
  install it. A deployment can no longer quietly serve the weaker search,
  and the first question no longer pays for loading the model.
- The Docker image installs the semantic packages and fetches the model at
  build time, at the pinned, reviewed commit, compressed to int8; the
  uncompressed copy is deleted from the image.
- `off` stays, for the test suite and CI: they pin exact rankings, run
  without the 118 MB download, and the hybrid behaviour has its own tests.
  The eval keeps the keyword column as the baseline the model is measured
  against.

## 2. Georgia on the map

The Texas map has three layers: every named lake from OpenStreetMap (ADR
0010), GBIF species records on those lakes (ADR 0012), and TPWD's verified
lakes with surveyed species, confirmed ramps and agency profiles (ADRs
0002, 0022). The first two were already state-agnostic apart from two
tables; Georgia gets them now.

- `osm_waterbody_import.SUPPORTED_STATES` and
  `gbif_occurrence_import.STATE_BOUNDS` gain Georgia.
- An OSM lake's "check before you go" line named Texas Parks and Wildlife
  for every lake. It now names the lake's own state agency from the
  jurisdiction registry (ADR 0027), or "<state>'s fish and wildlife agency".
- Nothing else changes: `/api/states` reports Georgia as having lakes once
  the import has run, which is what lights it up on the national map, and
  entering it there selects Georgia's rules everywhere (ADR 0027).

The imports need the Overpass and GBIF APIs, which neither the development
sandbox nor its shell on the developer's machine can reach, so they are run
by hand (README).

### What the import found (2026-10-19)

- OpenStreetMap: 2,350 named lakes and ponds, 302 ramps, piers and fishing
  spots (Texas: 3,777 OSM lakes besides its 161 verified ones).
- GBIF: 76,001 records for the 18 guided fish; 49,442 fell inside 105 lakes,
  25,450 inside none (streams and rivers, out of scope as for Texas), 1,109
  too imprecise. Licences: 47,360 CC BY, 1,638 CC0, 444 CC BY-NC.
- 82% of Georgia's download, and 96% of what landed on lakes, is one
  source: MARIS, the Multistate Aquatic Resources Information System, which
  pools state fish and wildlife agencies' sampling surveys (a consortium of
  those agencies; USGS support ended in 2014). Texas's download has none.
  Its records sit at a few dozen fixed stations per reservoir, which is why
  Georgia's records crowd onto 105 big reservoirs instead of spreading over
  many small lakes as iNaturalist and museum records do in Texas. Checked,
  not a bounding-box artefact: Clarks Hill's 3,893 records are at 56 distinct
  points, High Falls Lake's 2,085 at 10.
- They were filed under "Other museums and surveys". They now have their own
  group, "State agency fish surveys (MARIS)". Their years run 1986-2010
  (median 2000), so about half show as older evidence under the existing
  rule (WEAK_BEFORE_YEAR = 2000).

### Not yet: a verified layer for Georgia

Georgia WRD publishes forecasts for 32 reservoirs and 22 rivers, each with
its "best bet" species and maps of access points (ArcGIS StoryMaps). That is
the equivalent of TPWD's lake pages and the next step: an importer that
reads them into verified lakes the way `tpwd_statewide_import` does for
Texas, with the same rule that only an agency's own page can make a lake
verified or a ramp confirmed public.
