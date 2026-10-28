# ADR 0034: Official data as facts and links; California's official layer

## Status
Accepted. Applies the data-sourcing rules (docs/skills/fisheye-data-sourcing)
to everything imported so far, and adds California's official data.

## Context

FishEye is to become a commercial product. Three things stood in the way:

- **Agency wording in the database.** The TPWD import kept, as each
  species' evidence, the survey-report sentence that named the fish
  (1,125 rows), TPWD's own description of where each lake is (160 rows), and
  its predominant-species list items verbatim. TPWD's copyright policy
  reserves all of that. Facts are not copyrightable (Feist v. Rural, 1991);
  sentences are.
- **California had no verified lakes.** Its lakes were OpenStreetMap only.
  CDFW publishes a lake layer and stocking data under CC BY 4.0 or as
  public-domain state data.
- **"Unverified" said nothing about access.** Thousands of OpenStreetMap lakes
  sit in national forests and parks, where the public may fish; the panel
  treated them like a farm pond.

## Decision

- **Facts + link for every RESTRICTED source.** Evidence is FishEye's own
  sentence built from facts ("TPWD's 2022 survey report for this lake records
  Blue Catfish."), with the link. `app/cli/facts_only.py` rewrote stored
  rows (ORM updates: SQLite and PostgreSQL alike) and checks every stored text
  against the cached agency pages for any 8-word run in common. The
  importers now write only facts, so a re-import cannot bring the text back.
  Agency facts are credited "Data: <agency>" in the lake panel.
- **Provenance on every fact.** `source_records` gains a key, licence class,
  licence and citation (one row per dataset). `species_evidence` holds one
  row per fact (source, the source's own id, kind, year, sentence, link);
  `waterbody_species` stays the one-line summary the rest of the app reads.
  `waterbody_sources` credits datasets that describe a lake as a whole.
- **California (`cdfw_import.py`).** CDFW's California Lakes layer is matched
  to OpenStreetMap lakes (centre in the OSM box, plus the same name or, alone
  and of the right size, none), keeping DFGWATERID; named CDFW lakes missing
  from OpenStreetMap are added as unverified lakes credited to CDFW. A lake
  CDFW stocks (ds778, or the planting schedule) becomes verified. The
  planting schedule, the 2026 stocking plan and the High Mountain Lakes
  surveys (ds102) give species evidence. The schedule names only "Trout" or
  "Catfish": kept as that unless CDFW's stocking plan names the trout species
  for the same lake (a survey finding a species says it lives there, not that
  CDFW stocks it).
- **USGS NAS** non-native fish records join GBIF's "reported" tier.
- **State records and ShareLunker** are presence evidence only: lake,
  species, year, link. Angler names are dropped before anything is saved; no
  record or "big fish" feature exists. Before 2000 a record makes a species
  "reported", from 2000 "confirmed".
- **PAD-US** marks lakes on land open to the public, or open with limits
  (permits, seasons). The unverified-lake banner says so, and the private-pond
  warning is dropped on open public land. It is a fact about the land, never a
  confirmed entrance.
- An unverified lake now lists fish when an official source names them.

## Results (local SQLite, 2026-10-26)

- California: 377 lakes verified by stocking (from 0), 1,842 named lakes
  added from CDFW's layer, 1,689 lakes with a species list; 2,644 CDFW
  species facts (ds102 1,973, 2026 plan 376, planting schedule 295); 1,167
  NAS records in 313 lakes.
- PAD-US: CA 3,343 lakes on public land (1,418 open, 1,925 restricted, mostly
  wilderness); GA 270; TX 429.
- Records: TPWD water body records for 216 of 409 Texas water bodies with a
  mapped fish (1,413 facts); ShareLunker 5,819 of 6,060 entries (134 lakes);
  Georgia 17 of 46; California 23 of 42. Unmatched ones are rivers, private
  ponds, city-park ponds OpenStreetMap doesn't name, or names several lakes
  share, and are listed, not guessed.
- `facts_only`: 1,125 TPWD sentences rewritten, 160 locations removed, 352
  species lists rewritten; the check finds no stored text sharing 8
  consecutive words with a cached TPWD, Georgia WRD or record page.

## Known gaps

- 165 water names in the 2026 plan match no single California lake (streams,
  "Lake X Upper" variants CDFW names differently, several same-named lakes in
  a county); 8 stocked CDFW polygons have no name anywhere.
- PAD-US is tested at the lake's centre only. A lake whose centre is outside
  a forest boundary drawn along its shore gets no mark.
- docs/data-sources.md lists what still needs a human decision.
