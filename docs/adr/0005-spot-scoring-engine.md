# ADR 0005: Rule-based spot scoring, computed per request

## Status
Accepted

## Context
PRD §5.2 and build-plan item D specify a weighted, explainable scoring
model — no ML at MVP:

    Spot Score = Access 30% + Habitat 25% + Weather 20%
               + Species Match 15% + Freshness 10%

with one explicit requirement attached: *"若缺少测深或水草数据，不要把缺失项
当作零分，而应降低置信度并重新归一化已有信号"* — missing data must lower
confidence and renormalize, never score as zero.

This matters more than it sounds. Habitat data (bathymetry, aquatic
vegetation) doesn't exist in this project and isn't coming soon — there's
no free, structured source for it at the lake level. That's 25% of the
intended signal missing on *every* candidate. Scoring it 0 would push every
spot's score down by a quarter, and would systematically punish exactly the
lakes we know least about.

## Decision

### 1. A factor is either a value or `None` — never a silent zero
`app/services/scoring.py` models each signal as a `FactorScore` with
`value: float | None`. `None` means "no data"; `0.0` means "we have data
and it's bad". `combine_factors()` drops unavailable factors from the
weighted sum and renormalizes across the rest:

```
score      = Σ(value × weight) / Σ(weight)   over available factors only
confidence = Σ(weight)                        over available factors
```

Because the PRD weights sum to 1.0, `confidence` reads directly as *"the
share of the intended signal we actually had."* A typical candidate today
scores at `confidence = 0.75` — habitat is missing — and the response says
so, per candidate, in a `missing_signals` list. A test asserts the weights
sum to 1.0, since that's what makes this interpretation of confidence true.

The distinction is load-bearing in two places worth calling out:
- **Unconfirmed access scores 0, not `None`.** A private area is
  known-bad, not unknown. (It's also filtered out upstream — see §3.)
- **No target species requested drops the factor; a requested species with
  no local record scores 0.** Not asking about a fish isn't evidence
  against a spot; asking about one that isn't documented there is.

### 2. Candidates are computed per request, not stored
The PRD's data-model table lists `SpotCandidate` as a table with
`score`/`confidence` columns. This implementation does not create that
table, and the deviation is deliberate: two of the five factors (weather,
freshness) change on their own without anything in this database changing.
A persisted score would be stale within the hour with nothing to invalidate
it against. A candidate is therefore derived on demand from the one thing
that *is* stable — a confirmed-public `AccessPoint` — combined with a live
weather snapshot.

The table earns its place when something needs candidates that outlive a
request: precomputed rankings, A/B-testing weight changes, or answering
"why did this rank here last Tuesday". At that point it would also need to
store the weather snapshot each score was computed from, which is the part
a naive `SpotCandidate` table would have silently gotten wrong.

### 3. Access filtering is upstream of scoring
PRD §12 makes *"地图不会把未经确认的私人区域标为公共入口"* an acceptance
criterion, not a preference. `build_recommendations()` therefore queries
only `public_status == "confirmed_public"` points, rather than relying on
the access factor scoring them low. A weight change can never turn an
unconfirmed private area into a recommendation.

### 4. Severe weather is a top-level field, not a per-candidate note
PRD §17 requires warnings to take priority over normal recommendations. So
`safety_warnings` sits at the top of the response, not inside individual
candidates — a client can't render the list without having the warnings in
hand. Weather alerts are passed through, not scored: a thunderstorm warning
isn't a 20%-weighted input, it's a reason not to go.

### 5. Weather thresholds are sourced, and the sourcing is written down
The first version of the weather factor had numbers chosen by intuition.
They were replaced after actually reading the angling literature, and every
threshold now traces to **`docs/weather-scoring-rationale.md`**, which cites
what each one rests on and marks which breakpoints remain judgment calls.

Three conclusions from that research changed the code:

- **Wind scoring is non-monotonic, and that's the well-supported part.** A
  dead-calm lake scores *below* a light chop: wind-driven current
  concentrates plankton on the downwind bank, drawing baitfish and bass,
  and surface chop cuts light penetration so fish spook less. Two
  independent mechanisms, consistently reported. The upper bound is an
  angler-safety limit, not a fish-behavior one.
- **Barometric pressure is deliberately not scored**, despite near-universal
  belief in it among professional anglers. Water is ~800× denser than air,
  so a fish moving three feet vertically experiences a larger pressure swing
  than a passing hurricane — pressure is a *proxy* for fronts, wind and
  cloud cover, all of which are scored directly. Giving it its own weight
  would double-count them. A test pins this as a recorded decision so it
  doesn't get "fixed" later.
- **Frontal passage is scored instead**, from the forecast temperature
  trend — capturing what pressure was a proxy for, using data already in
  hand. Only *approaching* fronts: the hourly forecast looks forward, so the
  notorious post-frontal bite is undetectable without historical
  observations. Documented as a gap rather than faked.

NWS reports wind direction as the compass point the wind blows *from*, so an
"SE wind" pushes baitfish toward the **NW** shore. `downwind_shore()` inverts
it, with a test pinning the behavior. Getting this backwards would produce
confident, fluent advice sending an angler to the dead side of the lake —
the exact failure mode this project's "rules decide, LLM only explains"
structure exists to prevent.

### 5b. Partial availability: water temperature
Water temperature is the best-supported signal in the literature (largemouth
peak feeding at 65–75°F, with a full behavioral table in the rationale doc)
and **NWS does not provide it** — air temperature is not a safe substitute,
since water lags it by days to weeks and stratifies with depth.

Rather than approximating it or dropping weather wholesale, `FactorScore`
carries an `availability` fraction. Weather contributes its measured value at
full weight to the *score* — wind data is real data — while its contribution
to *confidence* is discounted by how much of the factor was actually
informed. A typical candidate today therefore reports **confidence 0.67**,
not 0.75: habitat is entirely missing, and weather is ~70% informed. The
number moves when the data situation changes, which is the whole point.

### 6. Time-window advice refuses to guess
`best_time_window()` scans the hourly forecast for the steadiest
contiguous block, with a nudge for dawn/dusk feeding windows. It returns
`None` when the weather snapshot is a fallback — checking `source`, not
just whether hourly data happens to be present, so placeholder data can
never become time-of-day advice.

## Consequences
- Every candidate today reports `confidence ≈ 0.67`. That's intended and
  visible, not a bug to paper over. Wiring in a habitat source (+0.25) or a
  water-temperature source (+0.06) is a data change; the scoring engine
  needs no rewrite, and confidence rises on its own.
- The weather thresholds are **priors calibrated to expert consensus, not
  fitted to outcome data** — there is no authoritative quantitative rubric
  for weather-to-fishing-quality published anywhere, and this project has no
  catch data of its own yet. The PRD's community pins are the natural source
  to eventually fit against; until then the rationale doc is what keeps
  these numbers honest rather than arbitrary.
- The scoring math is pure functions over plain dataclasses, with no DB or
  HTTP inside it, so the weight/renormalization behavior is unit-testable
  without fixtures. `app/services/recommendations.py` holds the DB
  assembly; `weather` is injectable there so tests never touch the network.
- Score alone is not a ranking key — ties break on confidence, and clients
  are expected to show both. A 0.96-at-0.55-confidence spot and a
  0.96-at-0.75 spot are not the same recommendation.
- Gear/bait rules (`GearRule`) and LLM-phrased explanations are explicitly
  *not* in this ADR. The factor `reason` strings are the structured input
  the Day 3 AI Advisor will phrase — per PRD §18, the LLM explains the
  ranking, it doesn't produce it.
