# ADR 0038: A catch's exact spot is the angler's, unless they share it

## Status
Accepted. Built and tested locally on 2026-10-29; not deployed.

## Context

Public catches showed everyone the spot to six decimals (about 10 cm), and
the map's bbox search ran on it too. The product review of 2026-10-28 found
this is what anglers hold against fishing apps most: "spot burning", a
favourite spot made public and fished out. Fishbrain and FishAngler both
answer it by making exact positions a paid feature, and both are criticised
for it. FishEye had no public catches yet, so the rule could change at no
cost to anyone.

## Decision

- A catch has `share_exact`, off by default. The owner and admins always see
  the spot. Everyone else sees a public point:
  - the spot itself, when the angler shared it;
  - else the linked lake's centre (a pin within 3 km of it, ADR 0016);
  - else the county's centre (the centroid of its largest outline ring);
  - else, outside every county, the spot rounded to 0.1° (about 11 km).
- The public point is stored (`public_latitude`, `public_longitude`,
  `public_place`), not worked out per request, so the map's bbox filter runs
  on it for other people's pins. Filtering by the exact spot would let
  anyone find it by asking for smaller and smaller boxes. The owner's own
  pins, and every pin for an admin, are filtered by the spot.
- Startup fills the point for pins saved before (`fill_public_points`),
  after their county (`fill_places`). Until then others see the rounded
  spot, never the exact one.
- API: every pin carries `location_shown` (what this viewer's coordinates
  are), `share_exact` and `public_place` (what everyone else sees). A form
  field and `PATCH share_exact` set the choice.
- UI: the catch form and the edit dialog have "Show other anglers the exact
  spot" (only for public catches). A catch shown at its lake or county gets
  a dotted marker; its page says "Lake Fork, not the exact spot" or
  "Somewhere in Wood County, TX" instead of coordinates, and its mini map
  opens zoomed out. The owner's page says what others see.
- Admins see the spot because "wrong location" and "private property"
  reports are about it.

## Consequences

- Several catches at one lake sit on one point; the map's clustering
  spreads them.
- Sharing the spot is free and stays free. It is never a paid feature
  (the review's rule: what is free now stays free).
- A lake re-import that deletes a lake leaves its pins' public point where
  the lake was; that is no leak and is redone if the angler changes the
  setting.
