# Experiment: can GBIF fill in species for Texas lakes?

Date: 2026-09-24 · Script: `backend/app/experiments/gbif_texas_coverage.py`
Run on the project owner's machine (the dev sandbox can't reach api.gbif.org).

## Question

The map shows 3,948 Texas lakes from OpenStreetMap (ADR 0010), but only the
10 verified lakes have species data. Before building an import, measure:

1. **Coverage:** how many lakes have at least one GBIF record of a species this
   app has a guide for?
2. **Quality:** on the 7 lakes whose species come from TPWD survey reports,
   how well does GBIF agree with TPWD?

## Method

- Downloaded every GBIF occurrence with coordinates, no geospatial issue and
  status PRESENT, for 11 of the 12 guide species, inside a Texas bounding box.
  Hybrid striped bass isn't a GBIF species, so it was skipped. Largemouth bass
  was also searched under *M. floridanus*.
- Dropped records with coordinate uncertainty over 1 km.
- Matched each remaining record to the smallest OSM lake bounding box that
  contains it. Bounding boxes include shoreline and inflowing river arms, so
  coverage is an upper bound.
- Compared the GBIF species at each TPWD-verified lake against TPWD's list.
  All OSM elements that are the same lake (e.g. "Somerville Lake") were merged.
  TPWD's list is the set of species named in a survey report's summary, so it
  isn't exhaustive. A GBIF species missing from it isn't necessarily wrong,
  which makes the precision figures lower bounds.

## Results

**Records**

| | |
|---|---|
| Fetched | 133,603 |
| Coordinates within 1 km | 98,816 |
| Inside a lake's bounding box | 25,961 (the rest are rivers, creeks and coast) |

**Where the matched records come from**

| Source | Records | Lakes covered |
|---|---|---|
| Fishes of Texas Project (UT Austin; expert-vetted museum and agency records) | 16,072 | 282 |
| Other institutions (e.g. Oklahoma museum, TNHC, TCWC) | 4,785 | 209 |
| iNaturalist research-grade | 3,375 | 308, of which 148 are covered only by iNaturalist |
| TPWD, published directly | 1,729 | 13 |

**Coverage**

| | Lakes with ≥1 record |
|---|---|
| All 3,948 lakes | 469 (11.9%) |
| Excluding 943 flood-control structures | 457 of 3,005 (15.2%) |
| **Largest 50 lakes** | **49 / 50** |
| **Largest 100 lakes** | **95 / 100** |
| Largest 200 lakes | 162 / 200 |
| Largest 500 lakes | 255 / 500 |

- Among the 469 covered lakes: 178 have 20+ records, 102 have 5–19, 96 have
  2–4, and 93 have only one.
- 366 of the 469 lakes (78%) have at least one record from 2015 or later.
  Only 20% of individual records are that recent: much of the volume is older
  museum and survey work.
- Of the largest 200 lakes, most of those without records are not fishing
  lakes: salt lakes and playas (Laguna Salada, Truscott Brine Lake, Soda Lake),
  coastal marsh lakes, and dry playa lakes. Real misses include Lake Meredith
  and Twin Buttes Reservoir.

**Agreement with TPWD (7 survey-verified lakes)**

| Records used | GBIF species that TPWD also lists (precision) | TPWD species that GBIF also has (recall) |
|---|---|---|
| All | 54/64 (84%) | 54/60 (90%) |
| Since 2000 only | 52/59 (88%) | 52/60 (87%) |
| Fishes of Texas only | 50/60 (83%) | 50/60 (83%) |
| iNaturalist only | 37/41 (90%) | 37/60 (62%) |

The GBIF-only species are plausible rather than obvious errors:
- Bluegill at Gibbons Creek;
- shad at Lake Bryan and Lake Houston;
- spotted bass at Conroe, Houston and Livingston, which may come from the
  rivers flowing into those lakes, inside their bounding boxes;
- crappie at Livingston.

**Licences of the matched records:** 87% CC0, 12% CC BY-NC (non-commercial),
1% CC BY. **128 of the 469 lakes are covered only by CC BY-NC iNaturalist
records.** That's fine for a portfolio project, but those lakes would have to
be dropped, or limited to commercially licensed records, before any commercial
use.

## Side findings about the OSM layer

- **943 of the 3,948 "lakes" (24%) are Soil Conservation Service
  flood-control structures**, mostly on private ranch land. Only 12 of them
  have any fish record.
- The layer also includes non-fishing water: salt lakes and playas, coastal
  marsh lakes, and at least one estuary. Sabine Lake (1,463 records) is the
  brackish estuary on the Texas–Louisiana line.

## Conclusion

GBIF is worth importing as a **"reported" tier**: evidence that a species has
been recorded at a lake, shown with its record count, most recent year and
source. It must never be presented as "confirmed" (PRD constraints 1 and 10).

- It covers essentially every large Texas reservoir, which is where most
  people fish.
- It agrees with TPWD 84–90% of the time, and the disagreements look like
  omissions in TPWD's summaries more than errors in GBIF.
- It's one integration for the whole country, not one per state.

Before building it:

1. **Show evidence strength, not just presence.** One 1950s specimen is much
   weaker evidence than 200 records including recent ones. Show the count and
   the last-recorded year, and consider requiring either 2+ records or one
   record since 2000.
2. **Tighten matching** from bounding boxes to lake shapes, to stop river
   records being credited to a lake. This needs the polygons, which the OSM
   import currently discards, or PostGIS.
3. **Keep the licence per record** so non-commercial records can be excluded
   later without re-importing.
4. **Clean the OSM layer:** hide or label flood-control structures, and
   exclude salt lakes and estuaries.
