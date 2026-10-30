# ADR 0039: Lake reports go to a person, not to the map

## Status
Accepted. Built and tested locally on 2026-10-29; not deployed.

## Context

The product review of 2026-10-28 found that most states' lakes are thin
(names from OpenStreetMap, no species, unknown access) and that the users
who know a lake best had no way to say so. Competitors' reviews complain
most about data that is wrong and can't be corrected (OnWater's AI lake
descriptions). FishEye's data rule is that facts come from sources
(`docs/data-sources.md`), so a correction can't simply overwrite a lake.

## Decision

- Under every lake's details, "Something wrong here?" opens a short form:
  wrong place, not open to the public, wrong fish, wrong name, no water
  here, or something else (which needs a word on what), plus details.
- On the map, once a state is being explored, "Missing a lake?" takes a
  name and details and uses the middle of the map as the lake's place.
- Anyone can send either, signed in or not: most visitors have no account,
  and they are the people who fish these lakes. Ten an hour per address;
  the address is not stored. A signed-in report records who sent it.
- Reports go to a `lake_reports` table and an admin tab ("Lake reports"),
  oldest first, with a link to the lake (or the reported point). An admin
  checks a source, corrects the data by hand, and marks the report fixed,
  or dismisses it. Both are written to the audit log. The overview shows how
  many are open.
- A report never changes a lake by itself. Like catches (ADR 0016), it is a
  person's claim and stays out of the official tiers.

## Consequences

- Corrections need an admin's time. If they pile up, the next step is
  grouping reports by lake and letting a reviewed source fix several at
  once, not letting reports edit lakes.
- Spam is possible from people without accounts; the per-address limit and
  the admin's dismiss button are the defence for now.
