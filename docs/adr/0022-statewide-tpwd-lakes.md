# ADR 0022: Every lake TPWD publishes, verified from TPWD's own data

## Status
Accepted. Extends ADR 0002 (TPWD ingestion) and ADR 0004 (access points)
from ten lakes to TPWD's whole lake list.

## Context

Of the 3,948 Texas lakes on the map, 10 were verified. Measured on the
developer database before this change:

| | lakes |
|---|---|
| verified (official species and access) | 10 |
| GBIF records only ("reported") | 459 |
| nothing known | 3,479 |

Counting lakes undersells and oversells at once: most of the 3,479 are
small ponds and stock tanks, often on private land, and most fishing
happens on a few hundred reservoirs. So coverage here is also measured by
area (OpenStreetMap bounding-box area, which overstates long lakes but is
the same yardstick before and after). By area, the 10 verified lakes were
13% of Texas's lake water.

TPWD publishes a page for about 175 lakes, and a survey report for nearly
every one. They were not used because the original scraper needed each
lake's coordinates and access points entered by hand, and TPWD's access
pages give driving directions, not coordinates.

Two things changed that:

- TPWD's lake pages are richer than the survey summaries: a "Predominant
  Fish Species" list, TPWD's own poor / fair / good / excellent rating of
  the fishing per species group, surface area, location, and a link to
  the latest survey report.
- TPWD publishes a statewide **Public Boat Ramps** dataset
  (gis-tpwd.opendata.arcgis.com), 2,235 ramps with coordinates, 1,142 of
  them on lakes, each naming its lake. That is official public access with
  coordinates: exactly what ADR 0004 said scraping directions couldn't give.

## Decision

**Fetch once, import offline.** `tpwd_fetch.py` saves TPWD's survey index,
lake list, 174 report summaries and 175 lake and access pages (525 pages,
2 seconds apart, identified User-Agent) to a gitignored folder.
`tpwd_statewide_import.py` reads only that folder and the ramp file. The
parser can then be developed and tested against exactly the pages TPWD
served, and a re-import never touches TPWD's server.

Query-string URLs are refused, as before (ADR 0002). TPWD's robots.txt at
fetch time no longer disallows every query string, only a few paths; the
rule is kept anyway, since nothing needed uses a query string. Every URL is
also checked against the live robots.txt, so a future disallow stops the
fetch.

**Species.** A guide species is linked as `confirmed` when TPWD names it
in either source, with the text that says so as evidence:

- the survey summary, sentence by sentence. A sentence counts only if it
  says the fish is there. Any sentence with "no", "not", "discontinued",
  "stocking", "regulation", "length limit" and similar is skipped: the
  reports say "No White Crappie were collected" and "Hybrid Striped Bass
  stocking was discontinued", and an alias match on those would invent
  fish. Deliberately blunt: it also skips a few sentences that do show
  presence. In a first pass, 72 of the 1,240 species mentions in the
  reports came from sentences with such words; reading them is what
  produced this list.
- the lake page's predominant-species list, where TPWD writes "Channel,
  blue & flathead catfish" or "White & hybrid striped bass". The shared
  noun is distributed over the modifiers and only exact curated aliases
  count. A generic "Crappie" or "Catfish" names no species and links
  nothing.

Alias matching now takes the longest alias first, on whole words. Plain
substring matching (since the first scraper) found "striped bass" inside
"hybrid striped bass", so every lake with hybrids also "had" stripers.
Lake Somerville and Lake Conroe lost a Striped Bass they never had.

**TPWD's profile is stored as TPWD wrote it** (`agency_lake_profiles`):
ratings, list items, acres, location, links. It is shown in the lake panel
under "What Texas Parks & Wildlife says", credited and linked. FishEye
doesn't reinterpret the ratings; folding them into the spot score is a
separate decision.

**Placing a lake.** TPWD's pages have no coordinates; the lake is matched
to an OpenStreetMap lake of the same core name, and TPWD's ramps for that
lake decide which one when several share it.

| Outcome | Rule | Lakes |
|---|---|---|
| `osm_name` | same name, near TPWD's ramps for it | 122 |
| `osm_name_only` | same name, the only one, TPWD lists no ramps | 22 |
| `ramps` | TPWD ramps, no OpenStreetMap lake: plotted at the ramps' median, and the panel says so | 7 |
| `existing` | one of the hand-curated lakes; its name and curated access kept | 9 |
| left out | ambiguous or no location; listed by the import, never guessed | 15 |

"Near" is a radius that grows with the lake's surface area (4 × the side
of a square of that area, at least 8 km). It also drops the dataset's own
outliers: a few ramps labelled "Lake Tawakoni" sit 130 km away.

Every `osm_name_only` placement was checked against the location on TPWD's
page. One was wrong (TPWD's Lone Star Lake is in Morris County;
OpenStreetMap's only one is near Mineral Wells) and is excluded by name.
Four TPWD names map to a differently named OpenStreetMap lake ("Lake LBJ"
is "Lake Lyndon B. Johnson"); each alias was checked against TPWD's ramps
for the lake, or, for Walter Long Lake, which has none, its location.

**Access.** TPWD's ramps on the lake become `confirmed_public` access
points. A ramp within 150 m of an existing confirmed point is the same
place and is skipped. On a lake that gets official ramps, OpenStreetMap's
reported entrances are removed, as for every verified lake (ADR 0010). On
a lake TPWD lists no ramp for (24), they stay, each still labelled
"reported, not verified", and the panel heading no longer calls the list
"confirmed". A closed lake gets no ramps.

**Re-running** replaces TPWD-sourced species links and updates ramps and
profiles in place; a lake keeps the placement it got the first time. Two
runs in a row change nothing.

## Result

On the developer database (the same OpenStreetMap and GBIF imports):

| | before | after |
|---|---|---|
| verified lakes | 10 | 161 |
| lakes with official species | 10 | 160 |
| share of lake area verified | 13% | 90% |
| verified among the 50 largest lakes | 6 | 47 |
| confirmed public access points | 14 | 896, on 138 lakes |
| lakes with TPWD's fishing ratings | 0 | 150 |

The two area rows count each lake once: they were measured after the
OpenStreetMap import learned to merge lakes mapped as several elements
(below). Before that, second pieces of Amistad and Falcon, unverified,
counted as two of the largest lakes, and the share was 80%. Among the
largest lakes still unverified, Sabine Lake is a coastal estuary and Lake
Cherokee is privately owned.

## Consequences

- The verified tier now means "TPWD publishes this lake", not "someone hand
  checked it". Hand-curated lakes keep their curated access and names.
- The ramps have no names, fees or hours: they are shown as "Public boat
  ramp (TPWD #NNN)" and the panel links TPWD's access page for the rest.
  Parking is unknown, so it is not claimed.
- Some large lakes are mapped in OpenStreetMap as several elements: a way
  and a relation of the same water, two basins (Lake Meredith, Twin
  Buttes), an English and a Spanish element (Falcon). The verified one
  carried the data and the others showed next to it as unverified. Fixed
  in the OpenStreetMap import, where it belongs (ADR 0010, "Lakes mapped
  as several elements"): 16 extra elements in Texas are now merged into
  their lake, and re-running it folds rows from earlier imports in.
  "Graham Lake", first listed here, turned out to be a different lake 20
  km from Lake Graham and is correctly left alone.
- 15 TPWD lakes are left out: 12 small state-park and city lakes that are
  in neither OpenStreetMap's import nor the ramp dataset, 2 whose name two
  OpenStreetMap lakes share with no ramps to choose between them, and Lone
  Star Lake. A hand-entered location would place them.
- The ramp file is downloaded by hand from TPWD's open-data site; the
  fetcher can't reach it from a script without depending on that site's
  download API.
- The survey-sentence filter misses fish that are there ("Spotted Bass were
  more abundant ... due to the lack of submersed vegetation" is skipped for
  "lack"). That is the intended side to err on.
