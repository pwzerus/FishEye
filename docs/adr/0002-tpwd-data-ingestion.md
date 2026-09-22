# ADR 0002: TPWD Lake Survey Reports as the real data source, narrowed to the College Station – Houston corridor

## Status
Accepted (all 7 target lakes have resolved report URLs; see "Known gaps" below for what's still open)

## Context
The MVP (Day 1) shipped with 3 hand-curated demo lakes (`seed_tx_lakes.py`).
That data is honest about being a placeholder, but a real product — and a
portfolio project meant to demonstrate real data-engineering judgment —
needs an actual ingestion pipeline from a real source, with provenance.

Texas Parks & Wildlife Department (TPWD) publishes two relevant datasets:

1. **Stocking history** (`stock_bywater.php?WB_code=XXXX`) — a clean,
   4-column HTML table (species / year / number stocked / size). Easy to
   parse. Tells you what was *released*, not what's actually in the lake
   now.
2. **Lake Survey Reports** (`lake_survey/pwd_rp_t3200_XXXX/`) — long-form
   PDF + an HTML summary page per lake, produced by TPWD's own regional
   Inland Fisheries offices from real gill-net/electrofishing/creel survey
   data. Tells you what's actually been found in the lake, with population
   health context. Much richer, but the HTML summary is prose, not a table,
   and the full PDF (30-40+ pages) mixes narrative, tables, and figures
   with no consistent per-year structure.

## Decision

### 1. Do not scrape `stock_bywater.php`
TPWD's `robots.txt` (fetched and read directly, not assumed) disallows
crawling any URL containing a query string. `stock_bywater.php?WB_code=...`
falls under that rule. Scraping it anyway would technically work but
means shipping a project whose data pipeline knowingly violates the
publisher's stated crawling policy — not a trade-off worth making for a
demo, and not a habit worth building. **This endpoint is out of scope**,
full stop, regardless of how convenient its table format is.

### 2. Scrape only the static Lake Survey Report index pages
These pages have no query string and are not covered by the disallow
rule. Each has a "Fish Community" / "Management History" narrative
section that names the sport fish species TPWD's own biologists confirmed
present. This is lower data density per page than the stocking table, but
it is (a) allowed, and (b) arguably more useful — it reflects standing
population, not historical release volume.

### 3. Extract species by curated substring match, not free-text parsing
The narrative prose isn't structured, and grammatically parsing arbitrary
government-report English to extract entities is a well-known way to
manufacture confident-sounding wrong answers — exactly what PRD §4.2 says
never to do ("从不从全州物种列表推断"). Instead:

- `KNOWN_SPECIES` is a hand-maintained dict of canonical species name →
  known text aliases (e.g. "Hybrid Striped Bass" ⇄ "Sunshine Bass",
  "Palmetto Bass").
- Matching runs sentence-by-sentence; a match keeps the *whole sentence*
  as `WaterbodySpecies.evidence`, so every fact stored is one click away
  from independent verification against the source page.
- Every row is tagged `confidence="confirmed"` (this is TPWD's own survey
  finding, not an inference) with `source_url` pointing at the exact page
  and a `SourceRecord` capturing retrieval time and publisher.
- A lake that returns zero matches prints a warning rather than silently
  writing "this lake has no fish" — a parsing failure and an empty lake
  look identical to a naive scraper, and only one of them is true.

This trades recall (a sentence written in an unexpected way won't match)
for precision (nothing gets recorded that isn't traceable to an exact
sentence). For a product whose entire value proposition is "don't lie to
anglers about which lakes have which fish," precision over recall is the
correct trade here — same reasoning as the `AccessPoint.public_status`
design (§12) never inferring public access from ambiguous data.

### 4. Scope narrowed to the College Station – Houston corridor
Rather than statewide (which the original PRD didn't actually require —
"德州" was aspirational framing, not a hard requirement), the target list
is the 7 major reservoirs along the College Station–Houston corridor:
Lake Somerville, Lake Bryan, Lake Conroe, Lake Houston, Lake Livingston,
Fayette County Reservoir, and Gibbons Creek Reservoir. Coincidentally,
TPWD's own regional office for several of these reports is literally named
the "College Station - Houston District" — this is a real administrative
region, not an arbitrary bounding box.

### 5. Politeness, not just compliance
`REQUEST_DELAY_SECONDS = 2.0` between lakes and an identifying
`User-Agent` (`tpwd_user_agent` in `Settings`, following the existing
`nws_user_agent` pattern) even though nothing in TPWD's terms requires
either. A scraper that introduces itself and doesn't hammer a state
agency's server for a demo project is the bar, not the ceiling.

## Known gaps (as of this ADR)
- ~~Lake Livingston, Fayette County Reservoir, and Gibbons Creek
  Reservoir report URLs unresolved~~ — resolved 2026-09-21:
  `pwd_rp_t3200_1326` (Livingston), `pwd_rp_t3200_1292` (Fayette County
  Reservoir), `pwd_rp_t3200_1296` (Gibbons Creek). All 7 lakes in
  `TARGET_WATERBODIES` now have a real `survey_index_url`.
- Live end-to-end run against the real TPWD site (as opposed to the
  saved-fixture unit tests) has been done for the original 4 lakes only
  — run from a machine with normal internet access (this sandbox's own
  network egress policy blocks `tpwd.texas.gov`), via `--dry-run`, with a
  spot-check of the Lake Bryan and Lake Houston results against the live
  report pages. Results were consistent with the source text: no false
  species extractions, and the only under-counts were prey species
  (Green Sunfish, Longear Sunfish) intentionally not in `KNOWN_SPECIES`.
  The 3 newly-added lakes have not yet had their own live run or
  spot-check — do that before trusting them in a demo.
- No scheduled/recurring run has been wired up yet (cron / Task
  Scheduler) — this is currently a manually-invoked script
  (`python -m app.data_import.tpwd_lake_survey_scraper`).

## Consequences
- Real, sourced, re-verifiable data replaces 3 of the original
  hand-curated demo lakes once the scraper is run for real.
- `WaterbodySpecies.confidence` and `SourceRecord` — fields that existed
  in the schema from Day 1 but weren't exercised by the seed script — are
  now doing real work, which is a better demonstration of the schema
  design than the seed data alone was.
- Future non-TPWD sources (e.g. crowd-sourced fishing sites like
  fishermap.org) can be added later as `source_type="community"` with a
  lower `confidence` tier ("reported" rather than "confirmed") without
  any schema change — this was designed for from Day 1, not retrofitted.
