# ADR 0013: Drop the habitat factor and the water-temperature sub-signal

## Status
Accepted — amends ADR 0005.

## Context

ADR 0005 modeled two signals as intentionally, permanently `None`:

- the top-level **habitat** factor (25% of the spot score) — no bathymetry
  or aquatic-vegetation data source exists or is planned;
- the **water-temperature** sub-signal inside weather (30% of weather's
  sub-weight) — NWS gives air temperature only, and substituting it would
  be actively misleading.

Both were deliberate at the time: PRD §5.2 requires missing signals to
lower confidence rather than score as zero, and modeling the gap as a real
factor returning `None` (rather than just omitting it) made the gap visible
and testable. That reasoning holds for a signal that's *temporarily*
missing. It stops making sense for one that is missing on every single
request, forever, with no planned source — at that point "renormalize
around the missing signal" isn't handling uncertainty, it's permanently
discounting every score for a feature that doesn't exist. Every candidate
reported `confidence ≈ 0.67` (ADR 0005 §5b) not because the app was
genuinely unsure about anything for this request, but because two factors
could structurally never contribute.

Looking at a live scored candidate made this concrete: "Habitat: No Data"
and a weather reason ending "(excluded: no water-temperature source)"
appear on *every single card, always*, which reads less like calibrated
uncertainty and more like a permanently broken feature.

## Decision

Remove both, rather than keep reporting a gap the project has no path to
closing:

- **`score_habitat()` is deleted.** Habitat is no longer one of the spot
  score's factors.
- **`_score_water_temperature()` is deleted.** Water temperature is no
  longer one of weather's sub-signals.

Their weight is redistributed across the remaining factors/sub-signals,
rounded to keep the numbers readable, rather than left as a dangling
fraction:

    Spot Score = Access 40% + Weather 25% + Species Match 20% + Freshness 15%
    (was:         Access 30% + Habitat 25% + Weather 20% + Species Match 15% + Freshness 10%)

    Weather sub-weights = Wind 60% + Precipitation 25% + Front 15%
    (was:                  Wind 45% + Water Temp 30% + Precipitation 15% + Front 10%)

Both removed pieces of research stay documented for reuse:
- `docs/weather-scoring-rationale.md` keeps the water-temperature behavior
  table (38–85°F+ bands) with a note to re-add it as its own weighted
  sub-signal if a real source (USGS gauges, TPWD survey temps) is ever
  wired in.
- This ADR, and git history, are where `score_habitat()`'s reasoning and
  code live if a bathymetry/vegetation source is ever wired in — at which
  point it should return as its own weighted top-level factor, not be
  patched back into one of the four that absorbed its weight.

ADR 0005's own text (its §5b, and the "Spot Score = ..." formula in its
Context) is left as written — it accurately describes the design at the
time it was accepted. This ADR is the record of what changed and why,
rather than a rewrite of that history.

## Consequences

- **Every remaining `None`-valued factor is now a genuine, request-specific
  gap** — no target species requested, no observation date on a record, or
  (still) not enough forecast hours to detect a front. `missing_signals`
  and `confidence < 1.0` mean something concrete again: this request was
  short a piece of real, sometimes-available data, not "this app is
  missing a feature it will never build."
- **Confidence changed for every candidate**, because two factors that
  could never contribute are simply gone from the calculation rather than
  discounting it. With a target species requested and a short forecast
  window (one hour, no front signal), confidence went from `≈0.67` to
  `0.9625` (access 0.40 + weather 0.25×0.85 + species 0.20 + freshness
  0.15). Without a target species, it's `0.7625` (species drops out
  entirely, the same as before). This is a one-time, visible change, not a
  silent drift: existing tests were updated to the new numbers rather than
  loosened — see `tests/test_recommendations_api.py` and
  `tests/test_scoring.py`.
- **Nothing about the missing-data mechanism itself changed.** PRD §5.2's
  requirement — a factor with no data drops out and confidence is
  renormalized around what's left — is still exactly how `combine_factors`
  works. This ADR only changes which signals are modeled as factors at
  all, not how an unavailable one is handled.
- Frontend and API are unaffected structurally: `WeatherRecommendations.tsx`
  renders whatever `factors` the response contains, and never special-cased
  `"habitat"` by name, so it needed no changes — one less place a
  scoring-engine change could have silently broken the UI.
- If bathymetry/vegetation or water-temperature data is ever wired in, the
  right move is to re-add each as its own weighted factor/sub-signal and
  shrink the others back down — not to overload one of the four/three that
  currently absorbed its weight with a second meaning.
