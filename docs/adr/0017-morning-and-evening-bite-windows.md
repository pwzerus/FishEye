# ADR 0017: Show a morning and an evening bite window

## Status
Accepted. Refines the time-window advice from ADR 0005.

## Context

The recommendations panel showed one "best window": the highest-scoring
contiguous 3-hour block in the next 24 hours of forecast. Whichever of
dawn or dusk scored a little higher won, and the other disappeared — the
UI showed "7–10 PM" day after day while anglers plan around both the
morning bite and the evening bite.

## Decision

`scoring.bite_windows()` searches two parts of the day separately, in the
forecast's own local time (NWS start times carry the lake's UTC offset):

- morning: blocks entirely within 04:00–12:00
- evening: blocks entirely within 15:00–23:00

Each gets its best 3-hour block using the same per-hour score as before
(wind bands, rain chance, a modest low-light bonus), so a windy morning
still gets a window — just a lower-scoring one — instead of vanishing.
Blocks must be consecutive hours; a part of the day that has no complete
block inside the 24-hour horizon is left out rather than padded. Results
are in time order with their mean score, and the UI marks one as "Better
bet" only when the scores differ by at least 0.03.

`best_time_window()` (the single best block) is kept: the AI advisor's
facts still use it, and the UI falls back to it if `bite_windows` is empty.

Times are displayed in lake time, read straight from the ISO string rather
than converted to the viewer's zone — someone in Michigan planning a Texas
trip should see the dawn bite at dawn.

## Consequences

- The API gains `bite_windows` on `/api/recommendations` and
  `/api/advisor/explain`; `TimeWindow` gains optional `label` and `score`.
  Additive, so older clients are unaffected.
- A midday block can still be the single best block, but it's no longer
  what the panel shows. That's deliberate: the panel answers "when should I
  go", and the sources behind the scoring (docs/weather-scoring-rationale.md)
  support dawn and dusk far better than midday.
