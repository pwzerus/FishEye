# ADR 0004: Fix TPWD lake location accuracy — add real AccessPoint data, handle closures

## Context

Real-world feedback (a friend field-checking the app) reported that pins
for some lakes landed in nearby residential areas rather than on anything
resembling public access. Investigating turned up something more serious
than a misplaced pin: `tpwd_lake_survey_scraper.py`'s `upsert_waterbody()`
creates a `Waterbody` row with a single hand-picked centroid coordinate,
but never creates a single `AccessPoint` row for any of the 7 TPWD-scraped
lakes (Somerville, Bryan, Conroe, Houston, Livingston, Fayette County
Reservoir, Gibbons Creek).

`build_recommendations()` (the spot-scoring engine from ADR 0005 in the
`feature/weather-api` branch) filters strictly on
`AccessPoint.public_status == "confirmed_public"`. With zero AccessPoint
rows, `POST /api/recommendations` silently returns an empty candidate list
for all 7 of these lakes — a functional gap, not just a cosmetic one.

Separately, TPWD's own access page for Gibbons Creek Reservoir states:
"Gibbons Creek Reservoir is closed to the public as of 12/25/21." The app
was still listing it as an ordinary recommendable lake.

## Decision

**1. Access points are hand-curated, not live-scraped-and-geocoded.**

TPWD's per-lake `access.phtml` pages (not disallowed by robots.txt, unlike
the query-string stocking endpoint) give only driving directions ("From
the Lake Conroe bridge on FM 1375 travel west approximately 4 miles, turn
right on Stubblefield Lake Road...") — no coordinates. Turning open-ended
directions prose into structured facilities + lat/lng automatically is a
fundamentally less reliable extraction than the existing curated
species-name substring match: a wrong guess here doesn't just miss a
fact, it plots a pin in the wrong place and calls it confirmed public
access, which is exactly what PRD §12 exists to prevent.

Instead, each lake's named facility (as given on its own TPWD access page)
was identified and then geocoded against an independent source — a park's
own listed address, a government/NGO facility listing (National Forest
Service, TPWD's public-boat-ramp naming), or a mapping/camping site with
its own published coordinates — by hand, once, during development. This
is the same character of work as the three Day-1 lakes in
`seed_tx_lakes.py`, just done for these 7 later. A new `NamedAccessPoint`
dataclass and `access_points` field on `TargetWaterbody` hold this data;
`upsert_access_points()` writes it as ordinary `confirmed_public`
`AccessPoint` rows.

If TPWD changes access for a lake, this list needs a human to revisit it
— exactly the situation `public_access_status` (below) exists to make
visible rather than silently stale.

**2. `Waterbody.public_access_status` distinguishes "closed" from "no data yet".**

An empty `access_points` list already meant two very different things: a
lake nobody has surveyed yet, and a lake TPWD says is closed. Added
`public_access_status: "open" | "closed"` on `Waterbody` (default
`"open"`) so these are distinguishable in the API. Gibbons Creek Reservoir
is the one lake set to `"closed"` — no `AccessPoint` rows are created for
it, even defensively (`upsert_access_points()` refuses to write
`confirmed_public` points for a closed lake even if `access_points` were
non-empty by mistake).

The frontend (`WaterbodyPanel.tsx`) shows an explicit closed-to-the-public
banner and skips rendering weather/recommendations entirely for a closed
lake — there's no point scoring fishing spots on water nobody may legally
fish.

**3. `upsert_waterbody()` became create-or-update, not create-only.**

Previously, if a `Waterbody` row already existed, the function returned
it unmodified — meaning a corrected centroid, a newly-discovered closure,
or a fixed `access_summary` would never reach an existing demo database
without a manual wipe. It now updates the mutable fields on every run,
while still leaving `field_tested` untouched on an update (that's a manual
QA flag this scraper should never flip back to `False`).

**4. Waterbody + access-point upserts no longer depend on species extraction succeeding.**

`ingest_one_lake()` used to call `upsert_waterbody()` only after confirming
the species-mentions pass found something — meaning a lake with 0 species
matches (a real, if unlikely, possibility if TPWD's report wording changes)
would get no `Waterbody` row at all, and therefore no access points either.
These are independent facts about a lake; the waterbody and access-point
upserts now happen unconditionally, and the species-mentions check only
gates whether species links get written.

## Consequences

- All 6 open TPWD lakes (Somerville, Bryan, Conroe, Houston, Livingston,
  Fayette County Reservoir) now have at least one real, geocoded,
  confirmed-public `AccessPoint`, so `POST /api/recommendations` returns
  actual candidates instead of a silent empty list.
- Gibbons Creek Reservoir is explicitly marked closed, both in the data
  model and in the UI, rather than being indistinguishable from "no data
  yet" or presented as an ordinary recommendable lake.
- The access-point list per lake is intentionally thin (1–2 points each)
  rather than exhaustively covering every ramp TPWD's page names — each
  entry needed an independently verifiable coordinate, and not every named
  facility (e.g. Lake Conroe's smaller private marinas) had one available
  through the sources checked. Extending coverage is a data task, not a
  code change — add another `NamedAccessPoint` entry once a coordinate is
  verified.
- This does not change any waterbody's own centroid coordinate. The
  original friend feedback ("pins land in residential areas") is
  addressed by the AccessPoint pins now being real, road-adjacent
  facilities rather than by moving the big lake-centroid marker, whose
  accuracy was never independently re-verified in this pass.
