---
name: fisheye-osm-lakes
description: Which OpenStreetMap water FishEye imports as a lake, including the extra rules for named water with no water=* tag (only lake-like names that pass every filter). Use before changing the lake filters, re-extracting or importing any state's OpenStreetMap lakes, or answering why a lake is missing from the map or shouldn't be on it.
---

# FishEye OpenStreetMap lakes: what counts as a lake

The map shows a lake only if it is real water you could fish. OpenStreetMap
holds far more water than that (rivers, canals, swimming pools, sewage
lagoons, tailings ponds, zoo exhibits, golf hazards), and much of it is not
tagged with what kind of water it is. This skill is the rulebook for which
water becomes a FishEye lake. Licences and credit are a separate skill:
`fisheye-data-sourcing`.

When in doubt, leave the water out. A missing lake can be added later; a
sewage lagoon on a fishing map makes the whole app look careless.

## Where the rules live

| Rule | Code | Tests |
|---|---|---|
| Tagged water, private water, size, merging | `backend/app/data_import/osm_waterbody_import.py` (`parse_elements`, `merge_pieces`) | `tests/test_osm_import.py` |
| Untyped water (no `water=*`) | `backend/app/data_import/untyped_water.py` (`judge`) | `tests/test_untyped_water.py` |
| Extraction from Geofabrik, state outline | `backend/app/data_import/geofabrik_lakes.py` | `tests/test_padus_geofabrik_nas.py` |

The code is the source of truth; this skill must say the same thing. Change
both together (see "Changing a rule").

## A. Water tagged as a lake (`water=lake`, `reservoir`, `pond`, or `landuse=reservoir`)

Imported when all of these hold:

1. It has a name. Unnamed water is never imported: mostly stock tanks,
   farm ponds and backyard ponds.
2. It is not private: no `access=private/no/customers/agricultural/forestry/delivery`,
   and "private" is not in its name (ADR 0032). A name pointing at private
   land (country club, golf, estates, ranch, farm, HOA, resort…) without a
   public word (park, county, city, state, public, wildlife…) is kept but
   marked `likely_private`, which the lake panel turns into a warning.
3. It is big enough: 200 m across for a lake or reservoir, 50 m for a pond
   (bounding-box diagonal).
4. It lies in the state (Census outline plus 2 km).
5. Pieces of one lake (same wikidata id; or same core name and overlapping
   boxes; or two big same-named basins within 3 km) become one lake.

## B. Named water with no `water=*` tag

`natural=water` alone says only "water here". Older and bulk-imported water
often has nothing more: Minnesota has 7,409 such named elements against
2,228 tagged lakes. Such water is imported only if **its name looks like a
lake and every condition below holds**. `untyped_water.judge(name, tags)`
returns the water type, or the first reason it fails:

| # | Condition | Left out (reason) |
|---|---|---|
| 1 | No tag says it is something else | `intermittent=yes`/`seasonal=yes` (intermittent); `salt=yes`/`tidal=yes` (salt_or_tidal); `leisure=swimming_pool/water_park/swimming_area`, `amenity=fountain` (pool_or_fountain); `landuse=basin`, any `basin=*` or `man_made=*` (man_made); any `golf=*` (golf); `covered=yes`, `location=underground/indoor` (covered); `disused`/`abandoned` or `disused:*`, `was:*`… (disused); any `wetland=*` (wetland); `tourism=zoo/theme_park/aquarium`, `zoo=*`, `attraction=*` (attraction) |
| 2 | No word in the name says it is not water to fish | retention, detention, stormwater, wastewater, waste, sewage, septic, treatment, settling, sediment, tailings, slurry, industrial, acid, drainage, catch pond, evaporation, infiltration, swimming, splash, aquarium, exhibit, golf, water hazard, "hole 7", fire/cooling/holding/koi/ash/reflecting/ornamental pond, lakebed, "(historical)", drained, former, "dry lake" (not_fishing) |
| 2b | Not water at a facility. A name with a facility word (club, school, college, university, campus, academy, seminary, cemetery, memorial gardens, church, chapel, hospital, prison, inn, hotel, motel, resort, estates, subdivision, HOA, apartments, condos, townhomes, mall, plaza, shopping, office, corporate, business park, plant, factory, airport, zoo, museum) is left out when **(a)** OpenStreetMap maps that kind of facility within 300 m of the water (`FACILITY_NAMES` ↔ `FACILITY_TAGS`, e.g. school → `amenity=school/college/university`, `landuse=education`; club → `club=*`, `leisure=golf_course/sports_centre`; cemetery → `landuse=cemetery`, `amenity=grave_yard`), or **(b)** the name names one particular facility: a proper name before the facility word, which OpenStreetMap often hasn't mapped — unless those words are a settlement (`place=city/town/village/hamlet/locality`) mapped within 20 km. A facility word that leads the name (after north/lower/little…) is a place name; the water goes on to rule 3. Exceptions: a housing word (estates, subdivision, apartments…) is never rescued by a place, the neighbourhood being the estate; "factory" counts only under (a), since "X Factory Pond" is usually an old mill pond and working factories are mapped (`MAPPED_ONLY`) | (a) "Athens Country Club Lake" beside a golf course, "Cemetery Lake" beside a cemetery (facility). (b) "Salisbury School Pond", "Fin and Feathers Club Lake", "Lakeside Estates Lake" (facility_name). Kept: "School Lake" (often a school land section), "School Section Lake", "Church Lake", "Club Lake", "Lake Seminary", "Tack Factory Pond", and "Little Ball Club Lake" 10 km from the hamlet of Ball Club, MN. Left out although a neighbourhood shares its name: "Winter Valley Estates Lake". A payload extracted before the check (no `facilities_near`) leaves every facility name out. |
| 3 | The name's head word is a lake word: Lake(s), Pond(s), Reservoir(s), Flowage, Flow, Impoundment (last word, after numbering such as "2", "No. 3", "Number One", "B", "II"); or it starts with Lake/Lago/Loch/Reservoir, perhaps behind a qualifier (north/south/east/west, upper/lower/middle, little/big, old/new, inner/outer), and does not end in another kind of water or place (river, creek, bay, cove, marsh, slough, lagoon, pool, fountain, basin, tank, spring, dam, park, beach, island…) | "Pine River", "Lake Creek", "West Lake Creek", "Lake Shore Pool", "Mallard Marsh", "Smith Tank", "Blue Hole" (not_lake) |
| 4 | Something besides the lake word, "the"/"of" and numbering is left | "Pond 3", "The Pond", "Lake A", "Reservoir No. 1", "The Flow" (generic) |
| 5 | Everything in section A (name, private rules, size, state, merging) | private_*, untyped_too_small |

Kept, for example: "Mud Lake", "Lake Butler", "Lake of the Woods",
"Fountain Lake" and "Storm Lake" (the head word decides), "Whortleberry
Pond", "Hay Creek Flowage", "Colton Flow", "West Lake Ellen", "Loch
Sheldrake", "Jesse McNeel Lake Number 2".

Water type comes from the head word: pond(s) → `pond`, reservoir(s), flow
and impoundment → `reservoir`, everything else → `lake`.

A word that can be a facility or a place name is decided by the map, not by
a word list: when adding a facility word, add the OSM tags that map that
facility to `FACILITY_TAGS` too, and a test with one kept and one left-out
name. The same goes for any new rule whose words are ambiguous: find what
in the data tells the two meanings apart, rather than dropping both.

Facility names (rule 2b) apply to untyped water only. Tagged water named
after a facility still follows section A: kept, with a `likely_private`
warning for club/estates/golf/ranch/farm/HOA/resort names.

Things deliberately **not** treated as lake words for untyped water: "Tank"
(Texas/Southwest stock tanks, mostly on private ranches), "Laguna",
"Lagoon", "Slough", "Pool", "Basin", "Spring". Tagged water using those
words is unaffected.

A lake kept this way is an ordinary unverified OpenStreetMap lake: no
species, "Unverified map data" label, OSM credit. `OsmLake.untyped` marks it
during an import; a merged lake counts as untyped only if every piece was.

## Workflow

1. **Count before importing.** Never import a rule change blind. From
   `backend/`:

   ```
   python -m app.data_import.geofabrik_lakes --count-untyped --states all --out-dir <scratch dir>
   ```

   It reads the cached Geofabrik extracts (`geofabrik_cache/`), writes
   payloads and `untyped_count.json` to the scratch dir, and never opens the
   database. Never point `--out-dir` at `osm_cache` (it refuses).
2. **Read the samples**, at least the big states (MN, NY, MI, ME, WI, FL,
   TX, GA, CA). For each kept sample ask "would a person go fishing here?"
   and for each left-out reason "did we drop real lakes?". Write the per-state
   numbers and anything surprising into a report under `reports/` and show
   it to the user.
3. **Wait for the user's go-ahead**, then back up the database, and import:

   ```
   python -m app.data_import.geofabrik_lakes --states all --force
   ```

   Payloads from an older `EXTRACT_VERSION` are extracted again
   automatically. Then re-run, in this order, the imports that match onto
   OpenStreetMap lakes, so they absorb their own rows into newly appearing
   ones: `cdfw_import` (California's CDFW-added lakes), `padus_import`,
   `usgs_nas_import`, `record_fish_import`, then `app.cli.facts_only --check`.
4. **Report** lakes per state before and after, SQLite size, and time.
   Update `docs/data-sources.md` (OpenStreetMap entry, import date, counts).

On the server, the same payloads are copied up and imported with
`osm_waterbody_import --from-file` (see `docs/deploy-aws.md`); the server
never needs pyosmium.

## Changing a rule

1. Change `untyped_water.py` (or the section A code).
2. Add a test case for the name or tag that prompted the change, kept or
   left out, in `tests/test_untyped_water.py`.
3. Update this skill, in both copies (`docs/skills/fisheye-osm-lakes/` and
   `.claude/skills/fisheye-osm-lakes/`), and ADR 0036 if the reasoning
   changed.
4. Count again (workflow step 1) and compare with the last report.
5. A re-import removes rows an earlier run kept that no longer pass, unless
   they are verified, carry a CDFW id, or have species facts (an official
   source vouches for those). Say how many were removed.

## Never

- Never import unnamed water, or name water ourselves.
- Never add species to an OpenStreetMap lake from its name or type.
- Never query Overpass for a whole state; bulk water comes from Geofabrik.
- Never loosen a rule without counting first and showing the user samples.
