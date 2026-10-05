# ADR 0010: A statewide "unverified" lake layer from OpenStreetMap

## Context

ADR 0009 made the map searchable, which exposed the real gap: outside the
handful of hand-verified lakes there was nothing to find. "Every fishing
spot in the US" is three different datasets with very different
availability:

| Layer | National source | Difficulty |
|---|---|---|
| The lake exists (name, location) | OpenStreetMap, USGS NHD | Easy, free, one-off import |
| Public entrances (ramps, piers) | OpenStreetMap `leisure=slipway`, `leisure=fishing`, fishing piers | Medium: uneven coverage, must filter private |
| Which fish live there | No national source; each state's fisheries agency (TPWD, DNRs) separately | Hard: why the verified lakes are hand-scraped |

The third layer can't be produced for a whole state, never mind the
country, without per-state work, and PRD constraint 1 forbids filling the
gap by inference. So the question became: can the map show lakes this app
knows nothing about *without* implying it knows something?

Decided with the project owner: start with all of Texas, get the full flow
working, then extend state by state. Show OSM entrances, clearly labelled.

## Decision

**Two data tiers on `Waterbody.data_tier`:**

- `verified`: hand-curated or scraped from an official source. Species
  evidence, confirmed-public access, scoring, AI explanations.
- `osm`: imported from OpenStreetMap to show that a lake exists.
  `public_access_status="unknown"`, never any species, and its entrances
  are `AccessPoint.public_status="osm_reported"`.

The tier is enforced where it matters, not just in the UI:

- The scoring engine already only ranks `confirmed_public` access
  (`services/recommendations.py`), so OSM entrances can never become a
  recommended spot. There is a test asserting exactly this.
- The AI advisor labels an OSM lake's source "OpenStreetMap
  (community-mapped)", never "official source". The frontend doesn't offer
  the advisor for OSM lakes at all: there is no ranking or species evidence
  to explain.
- The detail panel shows an "unverified" tag and banner, headings the
  entrance list "Entrances reported on OpenStreetMap", marks each one
  "reported, not verified" in amber (green stays reserved for confirmed),
  and says species are not verified rather than showing an empty list.

**The importer (`app/data_import/osm_waterbody_import.py`)** runs one
Overpass query per state and writes idempotently, keyed on OSM element
refs. It leaves out, on purpose:

- `access=private/no/customers/…` lakes and entrances (PRD constraint 4);
- unnamed water: in Texas overwhelmingly stock tanks and backyard or HOA
  ponds on private land;
- named lakes and reservoirs under 200 m across, and named ponds under
  50 m (fountains and garden features);
- entrances inside no imported lake (river and coastal ramps; this is a
  freshwater lake app);
- OSM entrances on verified lakes: those keep only official access data.

**Named ponds are included** (revised with the project owner after the
first version excluded all `water=pond`). A city-park pond is often the
best beginner spot there is, and TPWD stocks urban ponds for exactly that
reason. But many Texas ponds sit on ranches, in gated neighborhoods or on
golf courses, usually without an `access=private` tag. So ponds are stored
with `water_type="pond"`, their summary text and a separate amber warning
in the panel say they're often private, and a pond with no public-park
context is never presented as a place you may fish. Telling park ponds
apart automatically (via `leisure=park` containment) is possible but needs
real geometry to avoid false claims, so it waits for PostGIS.

Including ponds makes dense metro views larger than one request's cap
(2000). The backend returns verified lakes first, and the map shows a
"showing the first 2000, zoom in for the rest" message instead of silently
dropping the remainder.

Entrances are matched to the smallest lake whose bounding box (plus 300 m)
contains them. Bounding boxes, not shorelines, because there's no PostGIS
yet (ADR 0001); this is approximate and is described as such.

**Verified lakes are never overwritten or duplicated.** An OSM lake whose
core name matches a verified lake ("Somerville Lake" = "Lake Somerville")
and whose extent contains the verified lake's centre is linked via
`osm_ref` instead of imported. If the TPWD scraper later verifies a lake
the OSM layer already holds, the scraper promotes a same-named row in place
(dropping its OSM entrances), and the next OSM import removes any
differently-named OSM duplicate. Both paths are tested.

**The map loads by viewport.** `GET /api/waterbodies?bbox=west,south,east,north`
(Leaflet's `toBBoxString()` order), verified lakes sorted first so a capped
result can never drop one. Below zoom 8 only verified lakes load, with a
"zoom in" hint: a statewide view holds thousands of OSM lakes, and a
capped, arbitrary subset would look like the full picture when it isn't.
OSM markers are greyed and clustered (`react-leaflet-cluster`); verified
markers are never clustered.

## Consequences

- The map is usable anywhere in Texas, and honest about what it knows at
  each lake.
- Extending to another state means adding it to `SUPPORTED_STATES` and
  running the importer. At national scale (tens of thousands of lakes), the
  lat/lng range query and bounding-box matching should move to PostGIS, as
  ADR 0001 anticipated.
- OSM data is community-edited: a lake can be misnamed, a ramp can be
  closed or gated. The UI says so in every place it shows OSM data.
- Lakes deleted from OSM are not deleted here on re-import. That needs a
  "last seen in import" timestamp; deferred until it matters.
- No schema migrations exist (no Alembic, by design so far), so adding the
  new columns means recreating the dev database. See backend/README.md.
- Community fish reports (photos identified by an AI model, gated on being
  at the lake) were raised as the way to fill the species gap for OSM
  lakes. They belong to the community-pins phase and will be labelled
  "community reported", never "verified" (PRD constraints 1 and 10).
