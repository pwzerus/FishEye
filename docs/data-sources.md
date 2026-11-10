# Data sources

The register the data-sourcing rules require
(`docs/skills/fisheye-data-sourcing/SKILL.md`, rule 1: no entry here, no
import). For every source: where it is, what its terms say (quoted, with the
URL), its class, what FishEye stores from it, how it is credited, and when it
was last imported. The machine-readable half is `DATASETS` in
`backend/app/data_import/provenance.py`: each dataset there becomes one
`source_records` row carrying its licence class, licence and citation, and
every species fact and lake credit links to it.

What readers see of this register is `/sources` (ADR 0043), built from the
same records.

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
- Fetched again 2026-11-06 for the 22 classes added then (salmon, sturgeon,
  burbot, whitefish…) and the six fish that got guides; same filters.

### Wikimedia Commons photos — public domain, CC0 and CC BY only

- Data: the MediaWiki API (`commons.wikimedia.org/w/api.php`), each file's
  `LicenseShortName` read from its own metadata and checked by
  `fish_id_commons.licence_ok`: public domain ("Public domain", "No
  restrictions", PD-…), CC0, CC BY of any version. Refused: CC BY-SA (a
  fitted head is an adaptation, and share-alike would bind it), NC, ND,
  GFDL, anything unstated. Commons' own terms: each file is under the
  licence on its page (https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia).
- **Steelhead** (training and test): files whose title or description says
  steelhead; most are US Fish and Wildlife Service or NOAA photos (public
  domain). Split by creator, a third to test. Steelhead is the sea-run form
  of rainbow trout, so no species search finds it.
- **Steelhead, checked by eye**: of 177 files a "steelhead" search found,
  30 are a photo of one (the rest: Steelhead Falls, rivers, trail signs,
  maps, dishes, engravings); only those were kept. 4 of 17 iNaturalist
  observations tagged steelhead (GBIF full-text, CC0 / CC BY) were adults
  and kept, the others juveniles or unclear.
- **Second test set** (`fishid_cache/commons/`): up to 15 files from each
  fish class's species category; then about half, chosen by photographer
  (`--share`), moved to training, so web-style photos are learned from and
  the half left is still never fitted on. A Lake Erie "walleye" series that
  is plainly a freshwater drum was dropped from both.
- Young fish, eggs, dams, gear, drawings, dishes and specimens are left out
  by the words in the title and description.
- Fetched 2026-11-06. Tool: `fish_id_commons.py`. Creators of any photo the
  head is fitted on are in `TRAINING_CREDITS.json`, like iNaturalist's.

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

### Bait rules for 43 more states and DC — RESTRICTED (facts + link)

- What: each state's rules on what may be used as bait in fresh water (live
  fish, game fish, crayfish, moving bait between waters, releasing it), 2 to
  4 short sentences per state (`knowledge/jurisdictions.py`
  `STATE_BAIT_RULES`), each citing the page read (`species_guides.SOURCES`,
  ids `bait-<code>`). Shown on the bait-rules card and in Ask, only to
  someone who picked or named that state.
- Sources: the agency's own pages (myfwc.com, mdc.mo.gov, maine.gov,
  in.gov, mass.gov, dnr.state.mn.us, dnr.wisconsin.gov, gf.nd.gov,
  wildlife.utah.gov, doee.dc.gov, agfc.com), the state's administrative code
  (Kentucky 301 KAR 1:130, Washington WAC 220-310-070), and for the rest the
  state's official regulations guide on eRegulations (published for the
  agency). Agency and state-code pages are treated as RESTRICTED, like
  TPWD's: facts paraphrased in FishEye's own words, never copied, with the
  link.
- How collected (2026-11-01): one page at a time in a browser, reading only
  the bait passages; nothing stored but the paraphrase and the URL. Search
  results were used only to find pages, never as the source.
- Not written: Alaska, Delaware, Hawaii (rules found only in PDFs or not at
  all), Montana (2026 regulations PDF too large to read), South Dakota
  (handbook link returns 404). They keep the "check the agency" answer.
- Refresh: bait rules change most years (invasive species, VHS); re-read
  each state's page before each season, and when a state's page says it
  changed.

## Guides, handbook and license rules added 2026-11-01

### State agency fishing pages — RESTRICTED (facts + link)

- What: nine more fish guides (walleye, northern pike, yellow perch, brook,
  brown, golden and cutthroat trout, kokanee, bullheads), handbook topics on
  rigs and jigs, knots, ways to fish, the seasons and ice safety, and who needs
  a fishing license in 42 more states and DC (`knowledge/species_guides.py`,
  `angling_handbook.py`, `state_licenses.py`). Each names its pages in
  `SOURCES`, and each is shown with them.
- Licence class: RESTRICTED. Minnesota DNR ("© 2026 Minnesota DNR"), Missouri
  ("Copyright ©2026 Conservation Commission of Missouri. All Rights Reserved."),
  Pennsylvania ("Copyright © 2026 Commonwealth of Pennsylvania. All rights
  reserved."), Washington ("© 2026 All rights reserved."), Wisconsin DNR, New
  York DEC, and each state's license page. CDFW's `Fishing/Inland` pages are
  under its site terms, as elsewhere in this register.
- Stored: facts and numbers in FishEye's own sentences, with a link. No
  agency's sentences, tables or photos; MDC marks its photos "restricted to MDC
  only" and none is used.
- How collected: pages opened one at a time on 2026-11-01. Where an agency's
  license page couldn't be read (AZ, AR, ID, IL, KS, LA, ME, MI, NC, OH, RI, TN,
  among others), its eRegulations guide was read instead, and some of those pages
  are dated 2022–2025: **re-check these before relying on them**. Prices and dated
  free-fishing days were left out because they go stale.
- Left out because no page could be read: license ages for Massachusetts,
  Minnesota, Nebraska, New Hampshire and New Jersey (added 2026-11-06, see
  below); bait rules for Alaska,
  Delaware, Hawaii, Montana and South Dakota. Ask sends those questions to the
  agency. Also left out for want of an agency source: the Carolina rig, the uni
  and FG knots, and fish finders.

### Checked again 2026-11-06: every state's license and bait rules

- Every link in the rules (168 URLs: limits, license and bait pages) was
  fetched once: all answer. Eleven refuse scripts (Michigan, Massachusetts,
  New Hampshire, Kansas, Arizona, Nebraska: 403; Idaho: 503) and open in a
  browser, where they were read.
- Each license age was checked against the text of its cited page. Fixed:
  Colorado's Habitat Stamp is for ages 18 to 64; Hawaii's license starts at 9
  (a minors' rate to 15), seniors free; New Mexico's 70-and-older residents
  get a free license, not no license; Alabama's home-county exemption is for
  ordinary hook and line from the bank; Wyoming's and Utah's notes now say
  only what their page says. Where the agency page carries no age (Alaska,
  Oregon, Utah, West Virginia, Wyoming, Alabama), the source is now the page
  that states it (ADF&G's sport fishing license page, or the state's
  eRegulations license page).
- Added, from pages that now state the age: Massachusetts (15), Minnesota
  (16; non-residents under 16 only with a licensed parent; residents 90+
  exempt), Nebraska (16), New Hampshire (16), New Jersey (16, trout stamp).
  Every state and DC now has a license rule.
- Bait rules: every number and distinctive word in each state's sentences was
  looked for on its source page; the misses were read in context. Fixed:
  Rhode Island's "seines up to 8 ft by 4 ft" is not on its page and was
  removed (the page says nets may take only baitfish, and bans cast nets).
  North Carolina's gear sizes and 200-a-day limit are on its nongame page,
  now cited too (`bait-nc-nongame`). Maine's 16 baitfish species, Kentucky's
  seine and cast-net sizes, Oklahoma's closed lakes and Massachusetts's list
  were confirmed word for word.

## Gear photos, 2026-11-06

### Wikimedia Commons — public domain, CC0 and CC BY only

- What: one photo for 46 of the 52 items on /gear (rods, reels, line, hooks,
  weights, floats, lures, bait, tools), `knowledge/gear_photos.py`. Only the
  file name, a Wikimedia thumbnail URL, the author and the licence are
  stored; the picture is hot-linked with its credit, like the fish photos.
- Licence check: `fish_id_commons.licence_ok` on each file's own
  `LicenseShortName` (public domain, CC0, CC BY; no share-alike, NC or ND), so
  every photo is also usable for training later. Google Images was not used:
  its results carry no licence a commercial product can rely on.
- How chosen: up to 16 search results per item (`gear_cache/`, git-ignored),
  looked at by eye on contact sheets, one picked per item
  (`gear_cache/picks.tsv`, then `python -m app.cli.gear_photos`). Most
  results were wrong (old book scans, maps, cats for "calico"), so nothing is
  picked automatically. One file named no author ("own work"); its uploader
  is credited.
- No open photo found: circle hooks, wire leaders, soft plastic worms,
  lipless crankbaits, a tackle box, a bait bucket. The text still says what
  to look for.

### US Fish and Wildlife Service, US EPA — PD

- What: Clean, Drain, Dry steps (`fws.gov/story/clean-drain-dry`), and who issues
  fish advisories and how to find them (`epa.gov/choose-fish-and-shellfish-wisely`).
  Federal works; credited anyway. Stop Aquatic Hitchhikers (a campaign site, no
  licence stated) is used for facts + link only.

## Gear photo recognition: training photos, 2026-11-06

Photos used only to fit and test a gear recogniser (no photo is shown in the
app or kept in the repo; all sit in `backend/gear_cache/`, git-ignored). The
credit for each one is kept beside it, for a training-credits file shipped
with any model fitted on them (as `models/fish-id/TRAINING_CREDITS.json`).

### Open Images V7 (Google) — annotations CC BY 4.0, images CC BY 2.0

- Terms (storage.googleapis.com/openimages/web/factsfigures_v7.html):
  annotations "licensed by Google LLC under CC BY 4.0"; the images "are
  listed as having a CC BY 2.0 license", and Google asks users to "verify the
  license for each image yourself".
- What: photos with a gear label (Fishing rod, reel, lure, hook, float,
  sinker, bait, spoon lure, surface lure, spinnerbait, tackle box, tackle,
  fly fishing): human-verified yes, or a machine label of 0.8 or more; photos
  humans checked and found no gear in (hard negatives); and a sample of
  validation/test photos with no gear label (plain negatives).
- How: the label files and the image lists are read from the dataset's own
  bucket (the 2.5 GB train list is streamed, never saved); only rows whose
  `License` is exactly CC BY 2.0 are kept, with author, Flickr page and
  rotation (`gear_cache/oi/meta.csv`). Photos come from the dataset's public
  mirror on S3 (the one its downloader uses), one at a time, 1 s apart,
  shrunk to 640 px. Nothing is fetched from Flickr, so the photos the
  mirror lacks (it holds the 1.9M with boxes, not all 9M: about a third of
  those wanted) are left out.
- Labels checked by eye on 122 test photos (2026-11-07): the yeses from the
  Crowdsource app (`crowdsource-verification`) were wrong 35 times in 35 for
  Fishing rod (horses, a bus, a conference), so they are not used; the
  raters' `verification` and machine labels of 0.8 or more were right.
  `/m/02wg8` "Tackle" is the sports tackle (40 in 40 were football or rugby):
  those photos count as not gear. What is left of Open Images is mostly
  rods (about 280 trusted gear photos) and several thousand not-gear photos.

### Wikimedia Commons categories — public domain, CC0 and CC BY only

- What: files in Commons' gear categories (Fishing lure, reels, rods,
  floats, hooks, line, weights, bait, ice fishing equipment, swivels) and
  their direct subcategories, skipping heraldry, archaeology and museums.
- Licence check: `fish_id_commons.licence_ok` on each file (no SA, NC, ND).
  500 px thumbnails through the API, 1 s apart (`gear_cache/commons_cat/`).
- 1,136 files kept of 1,951 listed. Left out of training: museum stone
  weights, glass net floats, longlines, knot diagrams and shacks (by
  category), and drawings, engravings and catch shots (by a two-model photo
  check, ADR 0048).

### More gear photos found by their text, 2026-11-07

Four open catalogues were searched by their titles, tags and captions only
(`backend/tools/gear_id/scan_catalogs.py`, the names in `keywords.py`: 52
items, about 2,600 names in 13 languages, ambiguous words counted only next
to a fishing word). The photos found were downloaded at 640 px and every one
checked by eye before training (`fetch_candidates.py`, `handcheck.py`); a
first look at 299 of them found most text matches were not gear (a French
"ambassadeur", a dance called the jitterbug, "bobber" motorcycles), which is
why nothing is used on its text alone.

- **PD12M** (Spawning, `huggingface.co/datasets/Spawning/PD12M`, images on
  AWS `s3://pd12m`) — PD / CC0. The dataset is CDLA-Permissive-2.0; every
  image is listed as carrying a Public Domain Mark or CC0, sources include
  Wikimedia Commons, Smithsonian and Europeana; the maintainers ask users to
  verify licensing for their use. The 2.3 GB caption parquet was read; no
  copy kept.
- **YFCC100M, the OpenAI CLIP subset's metadata**
  (`huggingface.co/datasets/dalle-mini/YFCC100M_OpenAI_subset`), images from
  the AWS Open Data copy `s3://multimedia-commons/data/images/` — only rows
  whose licence is "Attribution License" (CC BY 2.0): about 15% of the
  subset. Non-commercial, ShareAlike and NoDerivs rows were counted, not used.
- **CommonCatalog CC-BY** (`huggingface.co/datasets/common-canvas/commoncatalog-cc-by`,
  card: cc-by-4.0; every row's own licence "Attribution License", CC BY 2.0):
  every CC BY photo of YFCC100M (14.6M) with the image inside the parquet.
  Only the text columns were read (about 6 GB); a found photo's bytes are
  read straight out of its page (`cc_images.py`, about 1 MB each).
- **Smithsonian Open Access** (`registry.opendata.aws/smithsonian-open-access`,
  CC0) — NMAH, NMAI, NMNH Anthropology, Cooper Hewitt, Postal: objects whose
  image's `usage.access` is CC0. Images from `ids.si.edu`, one a second. Most
  matching objects (10,000 of 10,100) have no CC0 image.

Each photo keeps its licence, author and page in
`gear_cache/open2/candidates.json`, for the model's training credits. See
"Needs human review" 12.

### What the model was fitted on, and its credits

`models/gear-id/TRAINING_CREDITS.json` lists all 1,982 training photos
(Open Images and Commons) with author, licence and page; it ships with the
model, like the fish model's. The camera reads a visitor's photo and keeps
nothing (privacy page). The model itself is Meta's PE-Core (Apache 2.0,
`timm/PE-Core-L-14-336` at a fixed revision, in `SOURCE.json`).

## Beginner questions from forums (QUESTIONS ONLY), 2026-11-08

Since 2026-11-08 the data-sourcing skill has a QUESTIONS ONLY class (the
user's decision): forum posts may be read to learn which questions beginners
ask. Only a paraphrase of each question is stored, as a test question for
Ask; never a post's words, answers, photos, user names or links. Answers come
from the guides. Claude reads one page at a time with the app's browser and
stops wherever robots.txt, a bot check or the tool says no. Each forum was
checked on 2026-11-08 as follows:

| Forum | robots.txt / access | Terms | Claude may read |
|---|---|---|---|
| BD Outdoors (Bloodydecks) forums, bdoutdoors.com/forums | `User-agent: *` disallows only cron and admin paths | https://www.bdoutdoors.com/forums/help/terms/: posters grant the site a licence "to use, publish, or re-publish your Content in connection with the Service" and "retain copyright"; nothing on crawling or AI | Yes: questions only |
| Reddit | the app's browser and the fetch tool both refuse reddit.com and redditinc.com | not read (blocked) | No; the user may read by hand and send questions |
| Texas Fishing Forum, GON forum (Georgia), Lake-Link, IceShanty | Cloudflare-managed: `Content-Signal: search=yes,ai-train=no,use=reference`; ClaudeBot, anthropic-ai and Claude-Web disallowed | not read | No (they turn away Anthropic's agents); by hand only |
| 2Cool Fishing, Ohio Game Fishing, Walleye Central | robots.txt sends AI agents to TollBit (pay per crawl) | not read | No; by hand only |
| BassResource forums | Cloudflare bot check (403, "Just a moment...") | not read | No (no bypassing bot checks); by hand only |
| The Great Outdoors Stack Exchange | posts CC BY-SA (help/licensing); robots.txt answers the app's browser with HTTP 418 and `Disallow: /` | Stack Overflow Public Network Terms, updated 2025-11-13; the data dump needs an account and a box ticked that it won't be used for LLM training | No by tool; the user may download the dump (questions only) |
| Xiaohongshu (小红书), Zhihu (知乎) | `User-agent: *` / `Disallow: /` | not read | No, by tool or by hand |
| Baidu Tieba (百度贴吧) | no rule for `*` (named search engines only) | https://tieba.baidu.com/tb/eula.html 8.2: without Baidu's consent its content and data may not be rewritten for publication or used for any commercial purpose | No, not even by hand (commercial use forbidden) |
| Douban groups (豆瓣小组) | `*` disallows search and /forum/, not group topics | https://accounts.douban.com/passport/agreement (updated 2026-07-02): no clause on crawling found; groups may switch on anti-copying, many need a login | Not tried; a group that needs a login is out |
| 钓鱼人 diaoyur.com, 钓鱼之家 diaoyu123.com | allowed | article sites (the site's own writing, all rights reserved), not forums | Not a forum: nothing to take |
| Yahoo! Chiebukuro (Japan) | ClaudeBot disallowed `/` | not read | No |
| Naver KnowledgeiN (Korea) | the app's browser refuses kin.naver.com | not read | No |
| 인낚 innak.kr (Korean sea fishing) | no rule for `*` | https://www.innak.kr/bbs/page.php?hid=provision article 7: a post's copyright belongs to its poster | Yes: questions only (sea fishing; little overlap) |
| Fishraider (now community.deckee.com), Maggotdrowning (UK) | Cloudflare-managed; ClaudeBot, anthropic-ai, Claude-Web disallowed | not read | No; by hand only |
| Ausfish (Australia) | Cloudflare bot check (403) | not read | No; by hand only |
| Anglerboard (Germany) | `*` allowed except posts/attachments/account paths | https://www.anglerboard.de/help/terms/: posts belong to their authors, the site gets a licence; nothing on crawling or AI | Yes: questions only (German waters and rules; technique questions overlap) |

BD Outdoors' sections lean to California saltwater; the bass club and the
CDFW Q&A board hold some beginner and California rule questions, roughly a
few per page of 25 threads (looked at once, 2026-11-08).

Read on 2026-11-08, one page at a time: BD Outdoors Fishing Tips p.1, Bass
Fishing Club p.1–2, CDFW Q&A p.1 and the first post of three threads;
Anglerboard "Angeln Allgemein" p.1 and "Raubfischangeln" p.1 (thread titles
only). Kept: 18 questions, each paraphrased (three of them are in
`eval/rag_cases.BEGINNER_CASES`, marked "paraphrased from a forum"). No
post's words, user name, link or photo is stored (docs/adr/0049).

Second pass, later on 2026-11-08 (robots.txt read again first: unchanged
on both forums). Read one page at a time, 5 s apart, thread titles only:
BD Outdoors Fishing Tips p.2–4, Bass Fishing Club p.3–5, CDFW Q&A p.2–3,
Kayak Fishing p.1, Fly Fishing p.1, Fishing and Hunting Cooking Recipes p.1,
Fishing Reels p.1, Fishing Reel Repair Tutorials p.1, Fishing Chit Chat p.1
(13 pages); Anglerboard Junganglerfragen (young and new anglers' questions)
p.1–3, Forellenangeln p.1, Montagen (Friedfisch) p.1, Rezepte p.1, Angeln
Allgemein p.2 (8 pages). Kept: 70 questions, each paraphrased in our own
words as a US freshwater beginner would ask it; saltwater trips,
tournaments, boats, hunting and German law were skipped. 14 of them are in
`BEGINNER_CASES` ("paraphrased from a forum"). What they found missing was
written from the booklets above and from the US Food and Drug
Administration's "Selecting and serving fresh and frozen seafood safely"
(`fda-seafood`, a federal work, PD): telling fresh fish from spoiled, and
what to wear (docs/adr/0049, addendum).

### Beginner topics, 2026-11-08 — RESTRICTED (facts + link) and PD

- What: the handbook cards on bites and hooksets, playing and landing a
  fish, a swallowed hook, no bites, stolen bait, snags, line twist, manners,
  kids, lightning, heat and cold water, and rod length
  (`knowledge/angling_handbook.py`, docs/adr/0049). Sources in
  `species_guides.SOURCES`: `mdc-tips`, `mdc-ethics`, `mdc-rigging`,
  `mdc-gear` (Missouri Department of Conservation), `utah-learn` (Utah DWR
  blog, 2023), `nydec-kids` (New York DEC), `pfbc-start` (Pennsylvania Fish &
  Boat Commission): state agencies, RESTRICTED, used as facts in our own
  words with a link. `nws-lightning`, `nws-heat`, `nws-coldwater` (National
  Weather Service) and `usfws-tips` (USFWS Northeast, on Medium): federal
  works, PD, credited anyway.
- Limits cards: one per state, `rule-limits-xx`, citing the agency's own
  size and bag limits page (`Jurisdiction.limits_url`; source ids
  `tpwd-limits`, `garegs-limits`, `cdfw-limits` and `limits-xx`). Only where
  the numbers are is stated, never the numbers.
- Not usable this time: Take Me Fishing answered the browser with 403;
  Idaho Fish and Game's site was down for maintenance; the agency guides on
  reel care and line replacement found were PDFs, not opened. Those topics
  stay unwritten. (Written later the same day from the booklets below.)

## Fishing-education booklets (PDF), 2026-11-08 — RESTRICTED (facts + link)

At the product owner's request, free learn-to-fish booklets published by
state fish and wildlife agencies were downloaded and read, to fill what the
beginner questions found missing (docs/adr/0050). Only official agency
copies were fetched, never a third-party mirror (Scribd, infobooks.org).
`robots.txt` was read on every host first: none disallows these files, and
none names Claude's crawlers or carries a Content-Signal line. One request
at a time, 5 s apart, User-Agent `FishEye-learning/1.0` with the project's
contact address.

The files are kept in `docs/learn-material/` (git-ignored, never committed:
they are the agencies' copyright), with `sources.tsv` there listing each
file's URL, retrieval date, size and SHA-256. 26 PDFs, about 106 MB.

| Source id | Booklet | Terms on the document |
|---|---|---|
| `tpwd-gear-care` | TPWD Angler Education: Fishing gear maintenance and repair | none stated; TPWD is RESTRICTED (above) |
| `tpwd-tips-beginners` | TPWD: Fishing tips for beginners (2020) | "© 2020 TPWD" |
| `tpwd-trout-tips` | TPWD: Winter trout stocking program, angling tips (2010) | "© 2010 TPWD" |
| `tpwd-ae-guide` | TPWD: Angler Education instructor guide (June 2022) | TPWD |
| `nydec-guide` | NYSDEC: I FISH NY Beginners' Guide to Freshwater Fishing (88 pp.) | none stated; its black-spot box is "Reprinted with permission of the New York State Department of Health" |
| `nydec-trout-synthetic` | NYSDEC: I FISH NY Guide to Trout Fishing with Synthetic Bait | none stated |
| `mndnr-minnaqua-safety`, `-tackle`, `-eating` | Minnesota DNR, MinnAqua Leader's Guide, lessons 6:1, 5:4 and 6:5 | "Copyright ©2010, State of Minnesota, Department of Natural Resources" |
| `odwc-fits` | Oklahoma DWC: Fishing in the Schools manual (2025) | "Copyright ©2026 by the Oklahoma Department of Wildlife Conservation. Reproduction in whole or part without permission is prohibited." |

- Downloaded, searched for the missing topics and skimmed, but not cited:
  the rest of the TPWD set (beginner's guide in English and Spanish, fly
  fishing for students), NYSDEC's basics sheet, panfish and stream-trout
  sheets, MinnAqua lessons 5:1, 5:2, 5:5, 6:3, the chapter introductions
  and glossary, and Wisconsin DNR's "Fishing for Dinner" instructor guide:
  what they cover the handbook already had, or it is about teaching a class
  rather than fishing. They are not read cover to cover.
- Kentucky's "Basic Fishing" (fw.ky.gov, the 2010 "state free" edition also
  posted by New Jersey) was read but **not cited**: it says "This material
  is intended to be used by not-for-profit organizations." Every fact taken
  from it is in one of the booklets above as well, and cited from there
  (Needs human review 15).
- What was written (`knowledge/angling_handbook.py`, docs/adr/0050): looking
  after a rod, reel and tackle; changing line; a push-button reel that won't
  cast; a hook in your skin; black spots in a fillet; lead sinkers; trimming
  a fillet; stocked rainbow trout; and a sentence each in Snags, Line twist,
  Keeping your catch, Rod power, Setting the drag, Is it a bite and Best
  time of day. Facts in our own words, never the booklets' sentences, tables
  or drawings; numbers only where a booklet gives them (line weights, a
  ⅛ oz sinker, 100 yards), never a figure that didn't survive text
  extraction (New York's lead-sinker weight).
- Still unwritten: why some fish taste muddy. No booklet says, and the
  sources found on it are about farmed fish.

## Question library, 2026-11-09

494 questions with English and Chinese answers, in
`backend/app/knowledge/qa_library.json` (docs/adr/0051). What each rests on:

- **The questions** are new wording, written from theme-level reading of an
  archive of two Reddit communities the product owner supplied (QUESTIONS
  ONLY): r/Fishing_Gear, 2015-04 to 2022-12, and r/FishingForBeginners,
  2015-07 to 2022-12. No post text, user name or link to a post is stored.
- **The answers** were written without opening those posts, and no answer's
  English shares more than 7 words in a row with any of the 111,056 archived
  submissions, or with the PDFs read for it. Each has a `basis`: `guide`
  (FishEye's guides and handbook), `official`, `maker`, or `general`.
- **`general` (231 answers)** is general fishing knowledge with no published
  source checked. The product owner decided on 2026-11-09 that these may be
  included. They are labelled on the page and in Ask.
- **Forum answers are not a source.** 35 answers improved from forum and
  article-site reading use their earlier wording here.
- **Pages cited** are in `backend/app/knowledge/qa_sources.json` and on
  `/sources#questions`. State agency pages and tackle makers' pages are
  RESTRICTED: facts in our own words, with the link.

Booklets read for it, as facts + link (the files are not in this repository):

| Source | URL | Class and basis |
|---|---|---|
| Handling Your Catch, Cornell / New York Sea Grant, 1986 | https://repository.library.noaa.gov/view/noaa/35462/noaa_35462_DS1.pdf | PD: the NOAA library page says "Public Domain"; no notice in the file |
| Fishing Is Fun for Everyone, USFWS | https://nrm.dfg.ca.gov/FileHandler.ashx?DocumentID=28814&inline | Federal publication; its photos are credited and not used |
| After the Catch, CDFW | https://nrm.dfg.ca.gov/FileHandler.ashx?DocumentID=28754&inline | PD under CDFW's Conditions of Use |
| Fishing exam catalogue, Sachsen-Anhalt | https://fischerpruefung.sachsen-anhalt.de/api/exam/question/export | Questions reusable under § 5 Abs. 2 UrhG, unaltered and with the source; only facts are used |
| Beginner's Guide to Fishing, South Carolina DNR | https://www.dnr.sc.gov/aquaticed/pdf/FishingGuide.pdf | RESTRICTED: site footer "All rights reserved" |
| Beginner's Guide to Saltwater Fishing, South Carolina DNR | https://www.dnr.sc.gov/fish/pdf/BeginnerguidetoSWfishing.pdf | RESTRICTED: as above |
| Lure, Shore, Bass and Pike Angling in Ireland, Inland Fisheries Ireland | https://www.fisheriesireland.ie/ | RESTRICTED: notice in each file; maps and photos not used |
| Getting Hooked, Inland Fisheries Ireland | https://www.fisheriesireland.ie/sites/default/files/2021-11/getting-hooked-fishing-handbook.pdf | RESTRICTED: no statement in the file |
| Fishing Is Simple Handbook, Future Fisherman Foundation | https://nrm.dfg.ca.gov/FileHandler.ashx?DocumentID=28748&inline | RESTRICTED: third-party work on CDFW's site, no statement in the file |
| CARE workbook, Connecticut DEEP | https://portal.ct.gov/-/media/deep/fishing/care/care2015workbookpdf.pdf | RESTRICTED: no statement in the file |
| CATCH student workbook, North Carolina WRC | https://ncwildlife.gov/catch-student-handbook/download | RESTRICTED: no statement in the file |
| Knot-Tying Guide, Illinois DNR | https://dnr.illinois.gov/content/dam/soi/en/web/dnr/publications/documents/00000150.pdf | RESTRICTED: no statement in the file |
| Sportfishing manual, University of Wyoming 4-H | https://4-h.ksu.edu/projects/natural-resources/sport-fishing/docs/sportfishing%20manual.pdf | RESTRICTED: no statement in the file |

## Not used

- **Flickr API**: no longer free for this use; Open Images already holds the
  Flickr photos that were CC BY, with their credits.
- **ImageNet**: its terms allow non-commercial research only.
- **Objects365, V3Det**: the annotations are CC BY 4.0, but the images keep
  their original Flickr terms and no per-image licence is given.
- **Google, Baidu and Bing image search; Taobao, JD, Xiaohongshu and Amazon
  product photos**: no licence a commercial product can rely on, and most of
  those sites' terms forbid scraping.
- **CDFW BIOS ds583 and ds2880**: marked "CDFW staff only". FORBIDDEN.
- **dbw.parks.ca.gov** (California boating facilities): its terms forbid
  spiders and commercial use. FORBIDDEN.
- **Commercial fishing books** ("Fishing for Dummies", "The Complete Idiot's
  Guide to Fishing Basics" and the like, which the New York guide
  recommends): not free, and a free PDF of one online is a pirated copy. Not
  downloaded.

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
9. **Open Images photos are CC BY 2.0 as listed, not as checked one by one.**
   Google lists each photo's licence but asks users to verify it; checking
   on Flickr would need its API. A model fitted on them ships their credits.
   Confirm that the listed licence plus a credits file is enough.
10. **Roboflow Universe "CC BY 4.0" fishing sets**: whoever uploaded them
    chose the licence, and nothing shows they held the rights to the photos;
    most are screenshots from fishing video games. Not used.
11. **Not used yet, look open**: COCO/LVIS photos whose own licence is CC BY,
    "no known copyright restrictions" or a US government work (LVIS has a
    fishing-rod class). Check each before use. (Smithsonian Open Access is
    used since 2026-11-07, above.)
12. **YFCC100M's metadata terms were not read.** Both Flickr sources above
    are built on YFCC100M, whose metadata Yahoo released under its Webscope
    agreement; the Webscope site no longer answers (2026-11-07), and the
    dataset's own page says use is "subject to the relevant Webscope License
    Agreement" without quoting it. The photos themselves are each CC BY 2.0
    as chosen by their authors, and only those are used, with credits.
    Confirm before shipping a model fitted on them.
13. **Not used, for their terms**: Unsplash Lite (training allowed for
    "internal business purposes" only; whether a public app counts is
    unclear), Pexels API (forbids building ML datasets), Pixabay API (forbids
    systematic mass downloads), Amazon Berkeley Objects (CC BY-NC), JD
    Products-10K and Alibaba AliProducts (research only), Wukong and other
    web-scraped Chinese image-text sets (no image rights), CSDN/GitHub
    "fishing" datasets (paid, and of anglers, not gear).
14. **Reddit's own terms were not read** (2026-11-08): both tools refuse its
    domains. Under QUESTIONS ONLY nothing of Reddit's is stored but a
    question in our words, and only a person reads it; confirm that this
    reading of its User Agreement is acceptable before launch.
15. **The state fishing booklets are used as facts + link** (2026-11-08).
    Oklahoma's manual says reproduction without permission is prohibited,
    and Minnesota's guide is copyright the State; nothing is reproduced,
    only facts in our own words, as for any RESTRICTED source. Kentucky's
    "Basic Fishing" says it is "intended to be used by not-for-profit
    organizations"; read as being about handing out the booklet, but to be
    safe it is not cited and nothing rests on it alone. Confirm both
    readings before charging for the app.
16. **The question library's questions come from a Reddit archive** the
    product owner supplied. Only new wording is stored, as under QUESTIONS
    ONLY, but the archive's licence was never confirmed and Reddit's terms
    remain unread (see 14). Confirm this before charging for the app.
17. **231 answers in the question library are general knowledge** that no
    expert has reviewed. They are labelled; review them, safety-related ones
    first.
