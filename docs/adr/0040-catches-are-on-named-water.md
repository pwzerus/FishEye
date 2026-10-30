# ADR 0040: A catch is on named water, and the map counts catches per water

## Status
Accepted. Built and tested locally on 2026-10-30; not deployed.

## Context

Catches could be pinned anywhere. The 2026-10-29 walkthrough found pins in
a mall and at a tackle shop, and catches the public saw only as "Somewhere
in Hall County": a pin was linked to the nearest lake *centre* within 3 km,
which a pin on a big reservoir's arm often missed and a pin in town often
hit. The map knew each lake as a point and a box; it knew nothing about
rivers, where a large share of fishing happens. Of the options drafted then
(A: real outlines and named rivers; B: lake boxes only; C: the photo's GPS
as a badge; D: other people's catches counted per water), the owner chose
A + D, with C as a badge.

## Decision

**Shapes.** `data_import/water_shapes.py` reads the same Geofabrik extracts
the lakes come from (ADR 0035) and keeps, per state:

- every imported lake's outline: all the OpenStreetMap elements the lake
  import merges into it, made valid and simplified (4 m for ponds, 12 m up
  to 1,000 km², 30 m above);
- every named river, stream and canal: its ways joined where they share an
  end or a waterway relation and have the same name (two "Mill Creek"s
  that never meet stay two), clipped to ways touching the state, streams
  under 1 km left out, intermittent streams left out unless a relation
  names them; plus the outlines of wide rivers' water, given to the river
  whose line runs through them;
- an outline for each verified lake with no OpenStreetMap twin, from any
  mapped water at or within 150 m of its centre (often an unnamed pond:
  Georgia's public fishing area lakes);
- each river's point in each county it crosses (a sample every kilometre,
  the one nearest the middle of that county's samples).

Everything is cut into pieces no bigger than a 0.05° grid cell and stored
as encoded polylines (`water_pieces`, `rivers`, `river_reaches`), so "what
water is here?" is an integer-index lookup of nine cells and a few pieces
decoded in plain Python (`services/water.py`), on SQLite or Postgres, with
no geometry library on the server. Imported 2026-10-30: 93,015 of 94,369
lakes outlined, 134,288 rivers/streams/canals, 537,449 pieces; 99 MB of
compressed payloads; the SQLite file grew from 79 to 301 MB.

**The rule.** A catch must be within 150 m of a lake's outline or a named
river's line or water (inside is 0 m). 150 m because anglers stand on the
bank, phones' GPS drifts by tens of metres, and a fingertip on a map at
placing zoom is wider than a creek. Inside an outline beats near one; a lake
beats a river at the same distance (rivers are often mapped running through
their reservoirs); a verified lake beats its OpenStreetMap double. A lake
with no outline is matched by its box, or within 300 m of its centre. A
state whose shapes aren't imported yet isn't held to the rule (old 3 km
link), so a deploy can't block catches before the import runs.

The rule is checked on save and when a catch is moved (`PATCH` with
`latitude`/`longitude`), and shown while placing: the pin is labelled with
the water's name or "Not on named water", and the form won't share until
it's on water, with "Water not on the map? Tell us" (a lake report, ADR
0039) for water the map lacks.

**What others see.** A lake catch at the lake's centre (as before); a river
catch at the river's point in the catch's county, never the spot (ADR
0038). On the map, other people's catches are one bubble per lake, per
river in a county, or (old catches on no water) per public point, with the
count, the most-caught fish and the latest date; tapping lists the newest
five. The viewer's own catches stay pins at their real spots. A lake's
panel says "N catches shared here →", and a county's catches list rivers
beside lakes.

**Photo taken here (C).** A photo's own GPS is read before its metadata is
stripped and kept on the photo row, never sent to anyone, the owner
included. A catch with a photo taken within 300 m of its spot shows "Photo
taken here"; one taken elsewhere shows nothing (a photo taken at home later
isn't held against anyone). Moving the catch or changing photos re-checks
it.

**Old catches.** At startup, catches not yet checked against the shapes in
a state that has them are linked to their water, or marked as on none
(`water_distance_m = -1`), and their public point is redone. Re-importing a
state's shapes marks its catches for checking again. The two catches in
the dev database moved from "Hall County" to Lake Lanier (53 m from shore).

## Consequences

- The server needs the shapes imported (`docs/deploy-aws.md`) and about
  220 MB more database. Until then, nothing changes there.
- Private ponds and unnamed water can't take a catch. That is the point for
  public catches; someone logging a private pond's catch for themselves
  can't, for now. "Tell us" covers named water the map lacks.
- OpenStreetMap's outlines are drawn by volunteers: a reservoir arm missing
  from its outline, or a creek with no name, will refuse a real catch. The
  150 m tolerance and the report link are the answers for now; the
  reports show where the data is wrong.
- The aggregation counts what a viewer may see; a private catch never
  appears in a count.
