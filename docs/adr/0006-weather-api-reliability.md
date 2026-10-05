# ADR 0004: Weather API — NWS adapter with cache, retry, circuit breaker, fallback

## Status
Accepted

## Context
PRD §4.3 needs current conditions, hourly forecast, and severe-weather
alerts to drive time-window/shoreline/lure advice. PRD §6 names the
National Weather Service (NWS) API (`api.weather.gov`) as the data
source — free, keyless, US-government open data, so unlike Google Places
or the LLM provider there's no secret to keep out of the frontend repo
for this integration.

PRD §17 requires that external services (weather, maps, LLM) have
timeout, retry, circuit breaker, cache, and fallback, and that core pages
keep working via a fixed-template fallback if the service is down —
severe-weather warnings must still take priority over normal
recommendations when they *are* available, but a downed NWS API must
never turn into a 500 on the map page.

## Decision

### 1. `app/services/weather_adapter.py` owns all NWS calls
`GET /api/weather?lat=&lng=` (per the PRD's documented contract) is a
thin FastAPI layer (`app/api/weather.py`) over `weather_adapter.get_weather()`,
which:
1. Calls `GET /points/{lat},{lng}` to resolve the forecast URLs for that
   point (NWS forecasts are per-gridpoint, not queried by raw lat/lng
   directly).
2. Calls the resolved `forecastHourly` URL and takes the first period as
   "current conditions" — NWS has no simple always-available
   instantaneous-observation endpoint, so like most consumer weather UIs
   built on this API, the nearest hourly period stands in for "now."
3. Calls `GET /alerts/active?point=lat,lng` for active severe-weather
   alerts.

### 2. Timeout + retry
Each NWS call uses a 5s `httpx` timeout and one retry after a short
delay before being treated as a failure — one slow/flaky call shouldn't
immediately tip the whole request into fallback.

### 3. In-memory cache (15 min TTL)
Successful snapshots are cached per point (rounded to ~0.01°, roughly
1km — finer than that buys nothing since NWS itself serves per-gridpoint
data). This is the same "single-process in-memory singleton" shortcut as
`app/services/tpwd_refresh_job.py`'s job tracker: fine for a portfolio
demo, and the PRD's own tech-stack section already calls out Redis as
optional infra for a real multi-worker deployment.

### 4. Consecutive-failure circuit breaker
After 3 consecutive NWS failures, the breaker opens for a 60s cooldown:
further requests skip the (doomed) live call entirely and go straight to
fallback, rather than piling up slow timeouts while NWS is down. After
the cooldown, the next call is allowed through as a probe.

### 5. Fixed-template fallback, clearly marked
If NWS is unreachable, or the circuit is open, `get_weather()` returns a
snapshot with `source="fallback"` and `stale=True` instead of raising —
`current.temperature` is `None` and `hourly`/`alerts` are empty rather
than fabricated. The API layer always returns `200` with this snapshot;
it never turns an NWS outage into a `5xx`. Callers (the frontend, and
later the PRD §5.2 scoring engine) must check `source`/`stale` and treat
weather as an *unknown* factor when it's `"fallback"` — not a favorable
or neutral one — since a scoring engine that silently defaults missing
weather to "good" would misrepresent confidence.

`weather_adapter.get_weather()` never raises; it's the one place that
absorbs NWS's unreliability so every caller doesn't need its own
try/except around weather data.

## Consequences
- The scoring engine (PRD §5.2, not yet built) can call `get_weather()`
  directly and rely on it always returning *something*, but must
  actually branch on `source == "fallback"` to renormalize weights
  per PRD §5.2's "missing signal" rule — this ADR only supplies the
  signal and its honesty flag, not the renormalization logic itself.
- The in-memory cache/circuit-breaker state is per-process and resets on
  restart — acceptable here, but would need to move to Redis (already
  flagged as optional infra) before running multiple backend workers.
- NWS only covers US coordinates; a point outside its coverage area will
  currently 404 on the `/points/` call and fall through to the same
  fallback path as a real outage. Good enough for this project's
  Texas-only scope; worth revisiting if the app ever expands outside the
  US.
