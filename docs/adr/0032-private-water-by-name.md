# ADR 0032: Private water, by its name

## Status
Accepted. Tightens ADR 0010's rule that private land is never shown as a
public place to fish.

## Context

The OSM import leaves out water tagged `access=private` (or no, customers,
...). Checked on Georgia: of 393 named ponds, 392 carry no access tag at all,
so the tag rule caught almost nothing. The names said more: "Private Pond"
(twice) and "Argo Lake (private)" were on the map as "access unknown", next
to dozens of country-club, estate, plantation and ranch lakes. Every OSM pond
already shows "many ponds are on private land", but a pond named "Private
Pond" needs more than that, and a country-club lake that isn't a pond got no
warning at all.

A second gap: the importer only added and updated. Water tagged private
after an earlier import stayed in the database.

## Decision

- **"private" in the name excludes the water**, exactly like an access tag
  (`private_by_name`).
- **A name that points at private land marks it `likely_private`**: country
  club, golf, club, estate(s), plantation, ranch, farm, HOA, homeowners,
  subdivision, resort, gated. Not if the name also says park, state, county,
  city, town, public, national, community, municipal, wildlife, WMA, PFA,
  refuge or recreation ("Taylor Farm Park Pond", "County Farm Lake"). Words
  are matched whole, so "Lake Clubb" and "Farmington Lake" are not caught.
- The lake panel shows a **"probably private"** tag and an orange warning
  ("assume it's private: only fish here if you know it's open to the public
  or you have the owner's permission"), in place of the softer pond warning;
  the map popup starts "Probably private ·".
- **Re-imports remove** OSM-only rows that are now excluded (tag or name),
  with their OSM entrances and GBIF records. Verified lakes are never
  touched by OSM tags: their access comes from the agency.

## Results (re-run offline from the saved files, 2026-10-19)

| | marked likely_private | removed as private |
|---|---|---|
| Texas | 107 | 0 |
| Georgia | 32 | 3 |
| California | 11 | 1 |

No verified lake was marked. Backend 603 tests, frontend 212.

## Known gaps

- A heuristic, so it can be wrong both ways. Josey Ranch Lake (Carrollton,
  Texas) is a public city park whose name lacks "park", and is marked
  probably private; the cost is a warning, not a hidden lake. A private pond
  with an ordinary name ("Smith Pond") still gets only the general pond
  warning.
- The fix for both is data, not more words: an agency's list of public
  waters (the verified layer) or a user report.
