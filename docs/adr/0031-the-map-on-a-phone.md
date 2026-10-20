# ADR 0031: The map on a phone

## Status
Accepted. Fixes the narrow-screen item left open since 2026-09-29.

## Context

Checked at 390 x 844 (an iPhone) before the first outdoor use. The home,
fish, guide and Ask pages were fine. The map page was not usable:

- the lake side panel is 360px wide and never shrinks, so on a 390px
  screen the map itself was about 30px wide;
- the "Community pins" and "Add a pin" buttons sat on top of the search
  bar's Search button, and the status banner was hidden behind "Use my
  location";
- the legend covered much of what was left.

## Decision

Below 760px wide (`globals.css`):

- The map and the panel stack: the map on top at 58% of the screen height,
  the panel below it, scrolling on its own. With a lake open, the map
  shrinks to 40%, because the lake's access points, species and plan
  matter more there than the map around it.
- Row 1 is the search bar at full width. Row 2 has "Use my location" on
  the left and the two pin buttons on the right as round icons; their names
  stay as `aria-label`s, so screen readers and tests still find them.
  Status messages move below both rows.
- The legend is smaller.

Desktop is unchanged.

## Known gaps

- At country scale the national map is wider than a phone and its zoom is
  locked, so the West is off screen until you pan. "Use my location" and
  search are the faster ways in on a phone.
- No offline mode: maps, weather and Ask all need a connection.
