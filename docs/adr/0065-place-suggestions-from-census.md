# 0065. Place suggestions as you type, from FishEye's own list of US places

Date: 2026-11-21. Status: accepted.

## Context

The search box (ADR 0009) sends a typed place to Nominatim through
`/api/geocode`. Nominatim's usage policy allows one request a second for the
whole app, wants results cached, and forbids suggestions as you type. So the
box only suggested from about 500 cities kept in the page
(`lib/usCities.ts`), and a chosen one still went to Nominatim.

On 2026-11-21 the owner asked two things: will place search hold up when many
people search at once (five a second, say), and can it suggest places from a
few letters, the way Google Maps does, since typing a whole English place
name on a phone is slow. It must be usable in a commercial product.

At one request a second, five new searches a second would queue and run past
the geocoder's 5-second timeout. Paid geocoders with suggestions exist
(MapTiler's, which FishEye already pays per request for satellite tiles), but
they bill per keystroke. Self-hosting Photon or Nominatim needs more memory
and disk than the 4 GB server has.

What anglers search for is a town, a county or a ZIP code (lakes have their
own search). The U.S. Census Bureau publishes all of them, public domain:
the 2025 Gazetteer files (every place, census-designated place, county,
county subdivision and ZIP code tabulation area, each with an internal
point) and ACS population estimates. Its Data API now needs a registered key;
its files don't.

## Decision

**A list of every US place, kept with the code.** `app/cli/us_places.py`
builds `app/data/us_places.tsv.gz` (1.1 MB, 69,737 names) from the Census
files in `census_cache/`: 32,019 places (cities, towns, villages, boroughs
and census-designated places, with the Census's "city" or "CDP" taken off
the name), 3,103 counties, 973 New England towns (where towns, not places,
are what people name; a town next to a place of its name is left out), and
33,642 ZIP codes, each named for the biggest place within 15 km of its
middle. Consolidated cities get the name people use ("Nashville", not
"Nashville-Davidson metropolitan government (balance)"). Population (ACS
2020-2024, table B01003) only orders names typed alike. Puerto Rico and the
island areas are left out, as FishEye covers the 50 states and DC.

**Suggestions are answered in memory.** `GET /api/places/suggest`
(`services/place_suggest.py`) matches the start of a name or of a later word
("fran" finds San Francisco), ignoring case, accents and punctuation, and
reads Saint/St., Mount/Mt. and Fort/Ft. alike; digits find ZIP codes. Names
are ordered by where the match is, then population, lifted for the state the
map is in and for places near where it's looking, so the nearest of the
Springfields leads. A query takes under a millisecond; the list loads in a
third of a second on first use and holds about 30 MB. The browser may keep an
answer a day, and a client may ask 240 times a minute.

**A chosen suggestion carries its point.** The search box asks after each
pause in typing (120 ms) and flies to a chosen place without asking any
geocoder. On Enter, a name typed exactly as one of the list's (with or
without its state) is found the same way. Nominatim is left for what the
list doesn't have: a street address, a landmark. The page's own city list
stands in only when the place list can't be reached, and still answers
cities typed in Chinese.

## Consequences

- Place search no longer depends on Nominatim for towns, counties and ZIP
  codes, so many people searching at once cost the server a few
  milliseconds, not a queue.
- The list is as current as the Census's yearly Gazetteer; rebuilding it is
  `python -m app.cli.us_places` after downloading the new files.
- A ZIP code's label names the biggest place near its middle, which is not
  always its post office's town (90250 is Hawthorne, labelled Los Angeles);
  the point it flies to is the ZIP code's own.
- Addresses still go to Nominatim and its limits. If they grow, MapTiler's
  geocoding (per request) is the next step.
