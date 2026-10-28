# ADR 0036: Named water with no water=* tag, by name and filters

## Status
Accepted. Imported into the local database on 2026-10-27 (94,369 lakes,
`reports/import-2026-10-27.md`); not deployed. Extends ADR 0035; the rules
are also the skill
`docs/skills/fisheye-osm-lakes/SKILL.md`.

## Context

The OpenStreetMap import took only water tagged `water=lake`, `reservoir` or
`pond` (or `landuse=reservoir`). A read-only scan of the Geofabrik extracts
on 2026-10-27 found 37,282 named `natural=water` elements with no `water=*`
tag at all, against 82,240 tagged ones. In Minnesota the untyped ones
outnumber the tagged three to one (7,409 against 2,228): older and
bulk-imported water was never given a type. Most of them are named like
lakes ("Mud Lake", "Whortleberry Pond"), but the same set holds rivers,
marshes, bays, swimming pools, fountains, tailings and sewage basins,
theme-park lagoons, zoo exhibits and golf hazards.

## Decision

- `untyped_water.judge(name, tags)` decides, in order: no tag says it is
  something else (intermittent, salt or tidal, pool, fountain, basin,
  man_made, golf, covered, disused, wetland, attraction); no word in the name
  says it is not water to fish (retention, stormwater, wastewater, tailings,
  "fire pond", "lakebed", "(historical)", "dry lake"…); it is not water at a
  facility: a name with a facility word (club, school, cemetery, church,
  hospital, inn, hotel, estates, HOA, apartments, mall, plaza, office, plant,
  zoo…) is left out when OpenStreetMap maps that kind of facility within
  300 m of the water, or when a proper name before the word names one
  particular facility ("Salisbury School Pond"; OpenStreetMap often hasn't
  mapped rural clubs and schools) and those words are not a place mapped
  within 20 km ("Ball Club Lake", Minnesota). A leading facility word is a
  place name ("School Lake", "Church Lake", "Lake Seminary") and stays.
  Two exceptions: a housing word ("Winter Valley Estates Lake") is never a
  place name, as the neighbourhood is the estate; "factory" counts only when
  industry is mapped near, as "Tack Factory Pond" and the like are old mill
  ponds and working factories are mapped. Then the
  name's head word
  is a lake word (Lake, Pond, Reservoir, Flowage, Impoundment), or it starts
  with Lake/Lago/Reservoir and ends in no other kind of water or place; and
  the name is more than a lake word and a number ("Pond 3" is left out).
  The head word gives the water type.
- What passes then meets every rule tagged water meets: private tags and
  names, likely_private marks, the size floor, the state outline, merging.
- "Tank", "Laguna", "Lagoon", "Slough", "Pool", "Basin" and "Spring" are not
  lake words for untyped water. Texas stock tanks are mostly on private
  ranches; the others are mostly not lakes.
- `geofabrik_lakes.extract` carries every named untyped `natural=water`
  element in the payload, so the import, not the extract, applies the rules.
  For water named after a facility it also reads the facilities of those
  kinds, and places, from the extract and records the kinds and place names
  mapped nearby (`facilities_near`, `places_near`), so the import can decide
  offline (`EXTRACT_VERSION` 5; older payloads are extracted again; without
  the fields a facility name is left out). A re-import
  removes rows an earlier run kept that the rules now leave out, except
  verified lakes and lakes an official source vouches for (a CDFW id or
  species facts).
- `geofabrik_lakes --count-untyped` counts what the rules would add, per
  state, with random samples of kept and left-out names, without opening the
  database. A rule change is counted and shown before it is imported.

## Consequences

- Tens of thousands more lakes once imported (counts in `reports/`), nearly
  all unverified, with no fish data, as every OpenStreetMap lake is.
- Name rules miss some lakes ("North Pond" stays, "Pond 3" goes; a stock
  tank stays out even where it is fished) and let some non-lakes through. The
  samples are the check; the rules can be tightened and re-imported.
- The Overpass path (`osm_waterbody_import` without `--from-file`) still
  asks only for tagged water; untyped water comes from Geofabrik extracts.
