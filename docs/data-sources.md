# Data sources

The register the data-sourcing rules require
(`docs/skills/fisheye-data-sourcing/SKILL.md`, rule 1: no entry here, no
import). For every source: where it is, what its terms say (quoted, with the
URL), its class, what FishEye stores from it, how it is credited, and when it
was last imported. The machine-readable half is `DATASETS` in
`backend/app/data_import/provenance.py`: each dataset there becomes one
`source_records` row carrying its licence class, licence and citation, and
every species fact and lake credit links to it.

Classes: **PD** public domain · **OPEN** licence allows commercial use ·
**RESTRICTED** facts + link only · (NC and FORBIDDEN sources are never imported).

Terms read on 2026-10-26. Not legal advice; re-read before each bulk import.

## Lakes

### OpenStreetMap, via Geofabrik extracts — OPEN (ODbL 1.0)

- Data: `https://download.geofabrik.de/north-america/us/<state>-latest.osm.pbf`, 50 states + DC.
- Terms (https://www.geofabrik.de/data/download.html): "All OpenStreetMap
  derived data on the download server is licensed under the Open Database
  License 1.0. You may use the data for any purpose, but you have to
  acknowledge OpenStreetMap as the data source. Derived databases have to
  retain the same license."
- Stored: named lakes, reservoirs and ponds (name, centre, bounding-box size,
  water type, OSM id); slipways, fishing spots and fishing piers inside them.
  Private water left out or flagged as before (ADR 0032). Named water with
  no `water=*` tag only when its name says lake and it passes the filters
  of ADR 0036 (skill `fisheye-osm-lakes`; dry run and samples:
  `reports/untyped-water-rules-2026-10-27.md`).
- Credit: "© OpenStreetMap contributors (ODbL)" on every OpenStreetMap lake's
  Sources tab and on the map. If the combined lake database is ever given to
  others, its OpenStreetMap-derived part must be offered under ODbL.
- Tool: `geofabrik_lakes.py` (download, pyosmium extract, `osm_waterbody_import`).
- Imported 2026-10-26: 64,742 lakes in 51 states (ADR 0035; 66,584 with
  California's lakes added from CDFW's layer).
- Imported 2026-10-27 with untyped named water (ADR 0036): 94,369 lakes in
  51 states (+27,785), SQLite 72.6 MB (`reports/import-2026-10-27.md`).
- Note: Geofabrik's `robots.txt` has `Disallow: *.osm.pbf`. It addresses
  crawlers; the extracts are offered for download "free of charge", and the
  data-sourcing skill names them as the bulk channel. Downloaded once per
  state, one file at a time, with a contact User-Agent. Listed under review.

### OpenStreetMap water shapes: lake outlines and named rivers — OPEN (ODbL 1.0)

- Data: the same Geofabrik extracts as above, read again by
  `water_shapes.py` (ADR 0040). No other download.
- Stored: each imported lake's outline (its OpenStreetMap elements'
  polygons, simplified to 4–30 m); named `waterway=river|stream|canal`
  ways joined into rivers per state (streams under 1 km and unnamed or
  intermittent streams left out), with the `natural=water` +
  `water=river|canal|stream|rapids` (and `waterway=riverbank`) polygons
  their lines run through; an outline from any mapped water for verified
  lakes with no OpenStreetMap twin. Cut into 0.05° pieces, encoded
  polylines. Each river's point per county comes from the Census county
  outlines below (PD).
- Used for: whether a catch is on named water, and where others see a
  river catch. Never shown as a map layer of their own.
- Credit: the map's "© OpenStreetMap contributors"; the shapes are part of
  the OpenStreetMap-derived database (share-alike if it is ever given out).
- Tool: `python -m app.data_import.water_shapes --states all` (extract and
  import); `--import-only` on a server, from `osm_cache/<code>_water.json.gz`.
- Imported 2026-10-30, 51 states: 93,015 lake outlines (of 94,369 lakes),
  134,288 rivers/streams/canals (28,705 rivers, 98,336 streams, 7,247
  canals), 155,000 river-county points, 537,449 pieces; payloads 99 MB
  gzipped; SQLite 79 → 301 MB. Verified lakes outlined from unnamed water:
  Georgia 52 of 80, California 47 of 62, Texas 2 of 3.

### CDFW California Lakes — OPEN (CC BY 4.0)

- Data: `https://services2.arcgis.com/Uq9r85Potqm3MfRV/arcgis/rest/services/CA_Lakes_wm/FeatureServer/0`
  (CDFW's current "California Lakes" layer). The hub item named in the task
  (`4d7024209b3d4b7796d4dd4119764d3e`) is marked deprecated by CDFW and its
  GeoJSON download now returns HTTP 400; its description points to this one.
- Terms (item licence, both versions): "License: This work is licensed under
  Creative Commons Attribution 4.0 International License
  (https://creativecommons.org/licenses/by/4.0/). Using the citation standards
  recommended for BIOS datasets (https://www.wildlife.ca.gov/Data/BIOS/Citing-BIOS)
  satisfies the attribution requirements of this license."
- Stored: DFGWATERID, official name, county, centre, surface acres, bounding box.
- Credit: dataset title, CDFW, CC BY 4.0, BIOS citation, on the lake's Sources tab.
- Tool: `cdfw_import.py`. Imported 2026-10-26: 27,506 features read; 2,428
  matched to OpenStreetMap lakes, 1,842 named lakes added; 377 lakes verified
  (stocked); 2,644 species facts from ds778/ds102, the schedule and the plan.
  Re-run 2026-10-27: 525 lakes added earlier are now on OpenStreetMap and
  were merged into those rows; 378 lakes verified.

## Public access

### PAD-US Public Access (USGS GAP) — PD

- Data: `https://services.arcgis.com/v01gqwM5QqNysAAi/ArcGIS/rest/services/PADUS_Public_Access/FeatureServer/0`
  (owned by USGS, updated 2026-07). ScienceBase's per-state downloads of
  PAD-US 4.1 need a JavaScript page to sign each link, so the service is used.
- Terms (ScienceBase item, https://www.sciencebase.gov/catalog/item/6759abcfd34edfeb8710a004):
  "Public Domain." Citation asked: "U.S. Geological Survey (USGS) Gap Analysis
  Project (GAP), 2024, Protected Areas Database of the United States (PAD-US)
  4.1: U.S. Geological Survey data release, https://doi.org/10.5066/P96WBCHS."
- Stored per lake: open / restricted, the area's name and manager (facts).
- Shown as "It lies in <area>, land open to the public (PAD-US)", never as a
  confirmed entrance.
- Tool: `padus_import.py`. Imported 2026-10-26: CA 1,418 open + 1,925
  restricted (mostly wilderness, which needs permits); GA 237 + 33; TX 358 + 71.
  Re-fetched and imported 2026-10-27 for the new lakes: CA 1,477 + 1,926;
  GA 299 + 50; TX 443 + 106.

## Near the water

### OpenStreetMap: bait and tackle shops — OPEN (ODbL 1.0)

- Data: the same Geofabrik state extracts as the lakes (`geofabrik_cache/`,
  nothing downloaded again), filtered offline with pyosmium.
- Terms: as for the lakes above (ODbL 1.0, credit OpenStreetMap).
- Stored: named shops tagged `shop=fishing` or `shop=bait`; outdoor, sports
  and hunting shops tagged `fishing=yes|bait` or `sport=fishing`, or named
  for fishing; any shop whose name says bait or tackle; the stores of Bass
  Pro Shops, Cabela's and Academy Sports + Outdoors by their `brand` tag. Name,
  point, kind (bait / tackle / store), address, phone, website, opening hours
  and the OSM element, all as mapped. Business details only, no people.
- Shown: on the exploring map from zoom 8, in the state being explored, with
  "© OpenStreetMap contributors · check hours before you go" and a link to the
  element. "Directions" is a plain link out to a maps app; nothing from
  Google is fetched or stored.
- Tool: `tackle_shops.py` (ADR 0037). Imported 2026-10-27 into the local
  database: 1,292 shops in 51 states (324 bait, 536 tackle, 432 stores; TX
  158, FL 92, CA 74). The payload a server imports is
  `osm_cache/tackle_shops.json`.

## Places

### US Census Bureau county boundaries (cb_2024_us_county_500k) — PD

- Data: https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_county_500k.zip
  (cartographic boundary file, counties, 1:500,000), downloaded once on
  2026-10-28 into `backend/census_cache/` (gitignored).
- Terms: a US federal government work, public domain; credit "Data: US
  Census Bureau".
- Stored: per county its GEOID, name ("Harris County", "Orleans Parish"),
  state and outline, simplified to ~100 m (`app/data/us_counties.json.gz`,
  2.3 MB, shipped with the code). A catch's state and county are looked up
  from it when the catch is saved, for browsing catches by state, county and
  lake (ADR 0037). Nothing else of the file is kept.
- Tool: `app/data_import/census_counties.py` (standard library only).

## Fish photo check

### BioCLIP 2 (imageomics/bioclip-2) — OPEN (MIT): the model shipped

- Model: https://huggingface.co/imageomics/bioclip-2 at commit
  `2957b322090f9cb17ae72c71981c7218a28d81e0`; the model card declares MIT.
  Gu et al. 2025, "BioCLIP 2: Emergent Properties from Scaling Hierarchical
  Contrastive Learning". A CLIP ViT-L/14. Built into `models/fish-id/` by
  `build_fish_id_model.py --model bioclip-2`, which refuses any licence but
  MIT or Apache-2.0 and loads only the weights, from the safetensors file
  (no code from the repo runs).

### BioCLIP (imageomics/bioclip) — OPEN (MIT): the lighter fallback

- Model: https://huggingface.co/imageomics/bioclip at commit
  `ce901ab3c6a913f9e9ef94ce6d27761069f4f01c`; the model card declares MIT.
  Stevens et al. 2024, "BioCLIP: A Vision Foundation Model for the Tree of
  Life" (CVPR). A CLIP ViT-B/16, built the same way (`--model bioclip`) for a
  server too small for BioCLIP 2 (ADR 0037 has both measured).

### iNaturalist photos via GBIF — CC0 1.0 and CC BY 4.0 only

- Data: GBIF occurrence search, dataset `50c9509d-…` (iNaturalist
  research-grade), `license=CC0_1_0,CC_BY_4_0`, US; each photo's own licence
  checked again. One photo per observation, iNaturalist's 500 px size. The
  data-sourcing skill: iNaturalist only through GBIF, licence-filtered.
- Test set (`fishid_cache/`, 2024 on, after BioCLIP's training data):
  measuring only, never shipped or shown.
- Training set (`fishid_cache/train/`, 2015–2023, other observations): the
  classifier head (`models/fish-id/head.npz`) is fitted on it, so it ships as
  an adaptation of those photos; every creator, licence and observation is in
  `models/fish-id/TRAINING_CREDITS.json`, which ships with it. No photo ships.
- Fetched 2026-10-27: 1,315 test photos and 3,439 training photos (50 fish
  classes; as few as 19 spotted bass and 21 threadfin shad are openly
  licensed). The head shipped is fitted on all 3,439.
- Tools: `fish_id_photos.py`, `fish_id_train.py`, `fish_id_eval.py` (ADR 0037).

## Fish in a lake

### CDFW Recent Stocked Waters, BIOS ds778 — OPEN (CC BY 4.0)

- Data: https://filelib.wildlife.ca.gov/Public/BDB/GIS/BIOS/Public_Datasets/700_799/ds778.zip
  (File Geodatabase, EPSG:3310, converted to WGS84 with pyproj).
- Terms (dataset metadata, `useLimit`): "License: This work is licensed under
  Creative Commons Attribution 4.0 International License … Using the citation
  standards recommended for BIOS datasets … satisfies the attribution
  requirements of this license."
- Citation used: "Recent Stocked Waters - California [ds778]. California
  Department of Fish and Wildlife, GIS Service Center. Published 2014-10-20."
- Stored: which DFGWATERIDs CDFW stocked, last year stocked. A stocked lake
  becomes verified.

### CDFW Fish Planting Schedule — PD (CDFW Conditions of Use)

- Data: https://nrm.dfg.ca.gov/FishPlants/PublicPlantSearch, the page's own
  Export button (`?Params.PlantTimeFrame=1&submit=Export`, CSV), once.
- Terms (https://wildlife.ca.gov/Conditions-of-Use): "In general, information
  presented on this web site, unless otherwise indicated, is considered in the
  public domain. It may be distributed or copied as permitted by law. However,
  the State does make use of copyrighted data (e.g., photographs) which may
  require additional permissions prior to your use."
- Stored: DfgWaterId, week, kind of fish ("Trout" or "Catfish": the schedule
  names no species, and FishEye doesn't guess one).

### CDFW 2026 Provisional Stocking Document — PD (CDFW Conditions of Use)

- Data: https://nrm.dfg.ca.gov/FileHandler.ashx?DocumentID=74004&inline (PDF).
- Stored: water, county, species from its tables. Its descriptive text is
  not stored.

### CDFW High Mountain Lakes fish, BIOS ds102 — OPEN (CC BY 4.0)

- Data: https://filelib.wildlife.ca.gov/Public/BDB/GIS/BIOS/Public_Datasets/100_199/ds102.zip
- Terms: same CC BY 4.0 statement as ds778 (dataset metadata).
- Citation used: "Fish - High Mountain Lakes [ds102]. California Department
  of Fish and Wildlife (CDFW). Published 2026-07-20."
- Stored: species and latest survey year per CaLakesID. Rows marked
  `FishNotPresent = Y` are never evidence.

### USGS Nonindigenous Aquatic Species — PD

- Data: https://nas.er.usgs.gov/api/v2/occurrence/search (state=CA, group=Fishes).
- Terms: U.S. federal data. Citation asked (site footer): "U.S. Geological
  Survey. [2026]. Nonindigenous Aquatic Species Database. Gainesville,
  Florida. Accessed [10/26/2026]."
- Stored: species, year, coordinates, record type and NAS key, as "reported"
  records (like GBIF), each linking to its NAS specimen page.
- Imported 2026-10-26: 5,694 California fish records read; 1,167 in 313 lakes.
  Re-run 2026-10-27: 1,166 in 315 lakes.

### State records and ShareLunker — RESTRICTED (facts + link)

Used only as evidence that a species lives in a lake. Stored: lake, species,
year, link. Never: angler names, weights, baits, photos, or the pages' text;
the fetchers drop those before writing anything to disk. No "big fish" feature.

- **TPWD Water Body Records**, https://tpwd.texas.gov/fishboat/fish/programs/fishrecords/recordsearch.phtml
  (one page per lake, `waterecords.php?WB_code=…`, 5 s apart).
  TPWD copyright policy (https://tpwd.texas.gov/site/policies/copyright-policy):
  "No part of this work may be copied, reproduced, or translated in any form
  or medium without the prior written consent of Texas Parks Wildlife
  Department except where specifically noted."
- **Toyota ShareLunker archives**, https://texassharelunker.com/archives/ —
  its own "Download CSV data for all ShareLunker Records" link. No licence
  stated (TPWD program). The CSV includes angler names and home towns; they
  were removed at download. All entries are largemouth bass.
- **Georgia WRD State Record Freshwater Fish**, https://georgiawildlife.com/fishing/recordprogram
  (the HTML table, newer than the PDF copies on gadnrle.org). No licence stated.
- **CDFW angling records**, https://wildlife.ca.gov/Fishing/Records (freshwater
  rows). CDFW Conditions of Use as above; stored as facts + link all the same.
- Imported 2026-10-26: TPWD 1,413 facts (216 water bodies), ShareLunker 134
  lakes (5,819 of 6,060 entries), Georgia 17 of 46, California 23 of 42.
  Every unmatched record is listed by the importer.
- Re-run 2026-10-27 against the larger lake set: TPWD 1,430 facts (219
  water bodies), ShareLunker 5,825 entries, Georgia 19, California 23. Names
  of qualifiers only ("Upper Lake") and "<X> Lake Park" read as "<X> Park
  Lake" are no longer matched.

### TPWD lake pages and survey reports — RESTRICTED (facts + link)

- Terms: TPWD copyright policy, quoted above.
- Since ADR 0034: species evidence is FishEye's sentence ("TPWD's 2022 survey
  report for this lake records Blue Catfish.") with the report link; TPWD's
  description of each lake's location is no longer stored; its species list
  is stored as FishEye's own sorted list of fish names. Kept as facts: surface
  acres, depth, year impounded, ratings, ramp locations. Credited "Data: Texas
  Parks and Wildlife Department". `python -m app.cli.facts_only --check`
  confirms no stored text shares 8 consecutive words with a cached TPWD,
  Georgia WRD or record page.

### Georgia WRD access sites and attractors — RESTRICTED (facts + link)

- Terms: no licence stated on the ArcGIS layers (ADR 0033).
- Facts only (where, what kind, which species, when placed); credited "Data:
  Georgia DNR Wildlife Resources Division".

### GBIF — per-record licence

Unchanged (ADR 0012): CC0 and CC BY records only in a commercial build
(`GBIF_EXCLUDE_NONCOMMERCIAL`).

## Rules: who sets them, and their pages

### Every state's fish and wildlife agency — links only

- What: each agency's name and the address of its fishing regulations page
  and fishing licence page, for the 48 jurisdictions FishEye hasn't written
  rules for (`knowledge/jurisdictions.py` `_AGENCIES`). Shown where FishEye
  says "check the agency": Ask's other-state answer, the limits note, OSM
  lake summaries.
- Licence class: not imported content. A name and a URL are facts (rule 3);
  nothing from the pages is copied or shown.
- How collected (2026-10-29): candidate addresses opened one at a time, a
  second apart, with a User-Agent naming FishEye and its contact address;
  pages that refuse scripts (Cloudflare and similar) opened in an ordinary
  browser; a CAPTCHA was never answered. Wrong or moved pages replaced with
  the agency's own page found by search, then opened again.
- Open: Idaho's two pages (idfg.idaho.gov showed a site-wide maintenance
  notice that night); South Carolina links its fishing page, which links the
  rules, because no statewide rules page loaded.
- Refresh: agencies move pages; re-check the list yearly, or when a report
  says a link is dead.

## Not used

- **CDFW BIOS ds583 and ds2880**: marked "CDFW staff only". FORBIDDEN.
- **dbw.parks.ca.gov** (California boating facilities): its terms forbid
  spiders and commercial use. FORBIDDEN.

## Needs human review

1. **Geofabrik `robots.txt`** disallows `*.osm.pbf`, while the site offers the
   files for free download and states "You may use the data for any purpose".
   Read as a crawler rule; confirm.
2. **CDFW California Lakes**: the skill's catalogue calls it "CDFW site terms:
   public domain"; the dataset itself says CC BY 4.0. Treated as CC BY 4.0
   (the stricter reading), credited as BIOS asks.
3. **TPWD and Georgia WRD**: facts + link is the conservative reading of an
   all-rights-reserved policy. Before charging for the app, ask both agencies
   in writing (TPWD: Communications Division, per its copyright policy).
4. **ShareLunker CSV**: the export carries angler names; FishEye never stores
   them, but the raw export is personal data. Confirm that downloading it at
   all (then discarding the names) is acceptable.
5. **PAD-US via the feature service** rather than the ScienceBase download:
   same publisher and licence; the service's version is not stated (updated
   2026-07, consistent with 4.1).
6. **TPWD water bodies 0312 "Gordon" and 2038 "Bullfrog Pond"**: since the
   2026-10-27 import two Texas lakes carry each name, and the records give no
   county, so they are unmatched (9 facts). Which water TPWD means needs a
   person (`reports/import-2026-10-27.md`).
7. **The photo check's classifier head is fitted on CC BY 4.0 photos.** CC
   BY allows commercial adaptation with credit; the credit is
   `models/fish-id/TRAINING_CREDITS.json`, shipped with the model. Confirm that
   a credits file (and, before launch, a credits page linking it) is the
   attribution the licence asks for, or refit on the CC0 photos alone.
8. **Fishbrain** (named by the product owner as the model for catches) is
   FORBIDDEN as a source: nothing of it is used, only the idea of pinning a
   catch with a photo.
