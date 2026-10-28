---
name: fisheye-data-sourcing
description: How FishEye finds, checks, collects and imports lake, access and fish data for any US state so that every record is legal to use in a commercial product. Use before adding a new data source, importing a new state, scraping any website, or showing third-party text in the app.
---

# FishEye data sourcing: legal, commercial-safe, repeatable

FishEye will be a commercial product. Every record we store must be one we
are allowed to use commercially, and we must be able to prove it later.
This skill is the rulebook. When it and a shortcut disagree, follow this
skill. When a case isn't covered, take the conservative path (rule 3) and
log it for a human (rule 10).

Not legal advice. It encodes a careful reading of each source's terms as of
2026-10. Terms change: re-read them before each new bulk import.

## The ten rules

1. **Read the terms before writing code.** For every new source, find and
   read its licence or terms of use (dataset metadata, "Use constraints",
   site "Conditions of Use"/"Copyright"/"Terms", robots.txt). Record the
   exact quote and URL in `docs/data-sources.md` (create it if missing).
   No entry there, no import.

2. **Classify the source** into exactly one class:

   | Class | Meaning | Examples | What we may do |
   |---|---|---|---|
   | PD | Public domain | US federal data (USGS, NOAA/NWS, EPA, USFWS), PAD-US, USGS NAS, 3DHP/NHD | Store and show anything. Credit anyway. |
   | OPEN | Open licence allowing commercial use | CC0, CC BY 4.0 (e.g. CDFW BIOS ds778, ds102), ODbL (OpenStreetMap), US state data stating public domain | Store and show; follow the licence (attribution; ODbL share-alike, see rule 7). |
   | NC | Licence forbids commercial use | CC BY-NC records in GBIF, MapTiler free tier | Do not use in production. GBIF: keep `GBIF_EXCLUDE_NONCOMMERCIAL` on for commercial builds. |
   | RESTRICTED | "All rights reserved", or permission needed for copying/commercial use, or no licence stated | TPWD (tpwd.texas.gov, texassharelunker.com), Georgia WRD pages and PDFs, most state agency web pages | **Facts + link only** (rule 3). |
   | FORBIDDEN | Terms forbid scraping/automated access or the data is marked internal | dbw.parks.ca.gov (no spiders, no commercial use), CDFW BIOS ds583 and ds2880 ("CDFW staff only"), Fishbrain, Navionics/Garmin, Google Maps/Places content, Reddit/forums, any login-walled site | Do not touch. Not even to "just check". |

3. **Facts + link for anything RESTRICTED.** US copyright protects
   expression, not facts (Feist v. Rural, 1991). From a RESTRICTED source we
   store only facts: lake name, coordinates, area, depth, year impounded,
   which species are present, survey or stocking year, ramp locations, a
   record's species and year. We never store or display its sentences,
   paragraphs, tables as laid out, photos, logos, or angler names. Every
   such fact carries `source_url` linking to the original page, opened in a
   new tab (never in an iframe). Evidence text shown to users is written by
   us from the facts, e.g. "TPWD's 2022 survey recorded Blue Catfish in this
   lake." followed by the link.

4. **Prefer the most official, most structured channel.** Order: official
   bulk download or API > official GIS service (ArcGIS REST, WFS) > the
   site's own Export button > HTML pages > PDFs. Never scrape what is also
   offered as a download.

5. **Be a polite client.** Obey robots.txt. One request at a time, at least
   1 s apart (5 s for small agency sites), a descriptive User-Agent with a
   contact address (feedback.fisheyefishing@gmail.com). Fetch once into a
   cache directory under `backend/` (gitignored), then import offline from
   the cache. Re-fetch only when refreshing. Back off on 429/5xx.

6. **Provenance on every row.** Each imported record links to a
   `source_records` row holding: source name, URL, licence class and
   licence name, retrieval date, and the source's own ID. Importers are
   idempotent (re-running does not duplicate) and keyed on the source's ID.

7. **Attribution and share-alike.**
   - CC BY: credit as the source asks (CDFW: https://www.wildlife.ca.gov/Data/BIOS/Citing-BIOS) on the lake's Sources tab and on the site's data-sources page.
   - ODbL (OpenStreetMap): show "© OpenStreetMap contributors" wherever OSM data appears. If we ever hand our combined lake database to others, the OSM-derived part must be offered under ODbL. Showing it in the app is fine.
   - PD: credit anyway ("Data: USGS").
   - RESTRICTED: credit "Data: <agency>" next to the link.

8. **Personal data stays out.** No angler names, no user-identifying info
   from any third party, even when the page shows it.

9. **Tests never touch the network.** Every importer ships with a small
   fixture file and unit tests (match logic, idempotency, licence fields).

10. **When unsure, stop and log.** If the licence is missing, contradictory
    (e.g. data.gov says CC-BY but the agency page says "staff only"), or the
    terms are unclear: do not import. Add the source to the "Needs human
    review" list in `docs/data-sources.md` with the quotes and URLs, and
    continue with other sources.

## Source catalogue

### Lakes (geometry, names)
- **OpenStreetMap** (OPEN, ODbL): bulk via Geofabrik extracts (`https://download.geofabrik.de/north-america/us/<state>-latest.osm.pbf`, or `us-latest.osm.pbf`), filtered offline with osmium (`natural=water` + `water=lake|reservoir|pond`). Do not bulk-query the public Overpass API for whole states. This is the current pipeline (`osm_waterbody_import`).
- **USGS 3D Hydrography Program (3DHP)**, replacing NHD (PD): official waterbody polygons with GNIS names. Use to fill names and lakes missing from OSM. https://www.usgs.gov/3d-hydrography-program
- **State agency lake layers**: check each one, e.g. CDFW California Lakes (CDFW site terms: public domain) https://data-cdfw.opendata.arcgis.com/datasets/4d7024209b3d4b7796d4dd4119764d3e_5

### Public access
- **PAD-US** Public Access layer (PD): is the lake on publicly accessible land? https://www.usgs.gov/programs/gap-analysis-project/science/pad-us-data-overview
- **State boat-ramp datasets**: check the licence of each (e.g. TPWD boat ramps on its ArcGIS hub: no licence stated, so RESTRICTED: locations as facts + link).
- **OSM** `leisure=slipway`, `leisure=fishing` (OPEN, ODbL).
- Private-land rules stay as they are: clearly private lakes are removed, name-suggests-private lakes are flagged.

### Fish species in a lake
- **State stocking data** (class varies): CDFW ds778 Recent Stocked Waters (CC BY 4.0), CDFW Fish Planting Schedule export (CDFW site terms: public domain; use the Export button, low frequency), TPWD stocking history (RESTRICTED: facts + link), GA weekly trout stocking PDFs (RESTRICTED: facts + link).
- **State lake surveys and fishing forecasts** (usually RESTRICTED): species present and survey year as facts, plus a link to the report.
- **CDFW ds102 High Mountain Lakes** (CC BY 4.0): species per surveyed Sierra lake.
- **USGS Nonindigenous Aquatic Species API** (PD): https://nas.er.usgs.gov/api/documentation.aspx
- **GBIF** (per-record licence): filter to CC0 and CC BY for commercial builds; iNaturalist data only through GBIF with that filter.

### Record fish (presence evidence only; no "big fish" features)
- State record programs and ShareLunker (RESTRICTED): store lake, species, year, link. Examples: https://texassharelunker.com/archives/, https://tpwd.texas.gov/fishboat/fish/programs/fishrecords/recordsearch.phtml, Georgia's state record list PDF. Shown only as "this species is present" with the source link.

### Conditions (optional)
- USGS Water Data (water temperature, levels; PD), NWS (PD), state reservoir level sites (check each; e.g. Water Data for Texas).

## Procedure for a new state

1. List the state's fish and wildlife agency, its open-data/GIS hub, and its site terms. Classify each candidate source (rule 2) and write it to `docs/data-sources.md`.
2. Lakes: OSM extract for the state, then 3DHP and agency layers to fill names and gaps. Remove clearly private lakes, flag likely-private ones.
3. Access: PAD-US overlay, agency ramps (by class), OSM slipways.
4. Species: stocking, surveys, USGS NAS, GBIF (licence-filtered), record programs.
5. Mark a lake `verified` only when an official agency source (OPEN, PD, or RESTRICTED used as facts) confirms it is managed or stocked for fishing.
6. Run the importers on the local SQLite DB first. Report per state: lakes, verified lakes, lakes with species, access points, and unmatched records (listed). Do not touch the server; give the human the commands.
7. Update `docs/data-sources.md`: what was imported, when, how many rows, and anything put under "Needs human review".

## Never

- Copy an agency's sentences, photos, or tables into our database or UI.
- Scrape a site whose terms forbid it, or bypass a login, CAPTCHA, or rate limit.
- Use data marked internal or "staff only", even if the file is reachable.
- Ship NC-licensed records in a commercial build.
- Run imports against production without a fresh `pg_dump` backup.
