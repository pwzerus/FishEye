# 0062. Coastal piers and jetties on the map

Date: 2026-11-18. Status: accepted.

## Context

The owner asked (2026-11-18) for the public places to fish from on the
coast, piers, jetties, seawalls and shore access, in every coastal state with
Alaska and Hawaii, listed and shown on the map: the coast has no lakes, so
the map had nothing for a saltwater angler.

The first OpenStreetMap pass (3,678 spots) was thin where it matters: Texas
had 6 piers and no jetty, Louisiana one pier, and of the 130 piers and
jetties California's CDFW lists as public, only 33 had a spot within 400 m.
Santa Monica, Malibu, Manhattan Beach and Redondo Beach piers were missing.
Two causes: a spot had to be inside the state's 1:10M outline, which a pier
reaching out to sea (and most of Texas's barrier islands) is not; and a long
jetty counted as coastal only if its middle was near the coastline.

## Decision

**Sources.** OpenStreetMap through Geofabrik's state extracts (ODbL), each
extract deleted once read, as the owner asked; and in California, CDFW's
Public Piers and Jetties (BIOS ds3090, CC BY 4.0). NOAA's Public Fishing
Access Site Register (about 5,300 sites on the Atlantic and Gulf coasts and
in Hawaii, public information) would fill the other coasts, but it is
reached through a guest login behind the US government system banner, so it
waits for the owner (data-sources.md, review item 18).

**What counts** (data_import/coastal_spots.py): piers marked or named for
fishing, or named piers and wharves that are not ferry, navy, marina or
numbered harbour berths; breakwaters and groynes marked for fishing or named
a jetty, and piers named a jetty; `leisure=fishing`; parks named a fishing
pier or a "Jetty Park"; bridges, walls and beaches marked `fishing=yes`; slipways as
boat ramps. Private ones and businesses (charters, guides) are left out. A
spot is coastal when any part of it is within about a kilometre of OSM's
coastline. Its state is the one whose Census county (1:500k, the outlines
catches already use) holds a point of it: a state's extract reaches a few
kilometres past its border, and a 5 km margin on the 1:10M outline, tried
first, gave Georgia's border ramps to Florida (the Hudson is narrower still).
A spot wholly at sea counts within 1.5 km of the outline, except on the few
foreign shores that close (Tijuana, Campobello). Multipolygon piers
(relations) are read too.

**One place, one marker** (data_import/coastal_spots_db.py). OSM's duplicates
fold: spots of one pier mapped twice, within 80 m, or 300 m when the names
share a word, unless the names differ by a number (Pier 1, Pier 2). Each
CDFW pier takes the nearest OSM pier, jetty or fishing spot within 200 m, or
600 m when the names share a word (apostrophes aside) or two jetties name the
same side, one to one: the spot gets CDFW's name and
license facts and OSM's position, hours, fee and lights.

**License facts.** A California public pier needs no fishing license (14 CCR
1.88); the popup says so in place of "check the posted rules", with CDFW's
note on where next to it one is needed again (the rock wall where a jetty
meets the shore, a breakwater, a footbridge), worded in each language.
Credits: "Data: California Department of Fish and Wildlife" linking to the
dataset, and the OSM credit when the pier is mapped there.

**Map.** A sea-blue square marker, a "Piers" layer button that shows only
when there are spots in view, and the legend entry. With a fifth button the
row of map buttons ran into "Use my location" on phones and off the map on
tablets, so on screens up to 1100 px the buttons are icons in a column down
the right edge; the satellite button's "free in beta" tag hangs under it and
steps aside while a popup is open, and popups keep 64 px clear of the column.

## Consequences

- 3,624 spots in 23 states (local import, 2026-11-18): 652 piers and jetties
  (384 in the first pass, counted the same way), 114 other fishing spots,
  2,858 boat ramps. Texas went from 4 piers and jetties to 18, Oregon from 8
  to 28, California from 57 to 175 with CDFW's 130.

- A server imports with one command, which fetches CDFW's 38 KB file once:
  `python -m app.data_import.coastal_spots --from-file osm_cache/coastal_spots.json`.
  The JSON is copied up with the deploy; no extract is needed there.
- Texas's Texas City Dike and Galveston's jetties are not in OSM as dikes or
  jetties, and the Gulf and Atlantic states other than Florida stay thin
  until NOAA's register (or a state's own list) is added.
- The license line is only as current as CDFW's dataset (updated 2024-01-09).
