"""National Weather Service (NWS) adapter (PRD §6, §17).

NWS's API (api.weather.gov) is free, keyless, US-government open data — no
API key ever needed here, so there's nothing to keep out of the frontend
repo for this particular integration (unlike Google Places / the LLM
provider, which do need real keys per the PRD's security constraint).

Reliability properties required by PRD §17 ("external services need
timeout, retry, circuit breaker, cache, and fallback"):
  - timeout:         short per-request httpx timeout, so one slow NWS call
                      can't hang the request.
  - retry:           each NWS call is retried once after a brief pause
                      before being treated as a failure.
  - circuit breaker:  after several consecutive failures, we stop calling
                      NWS for a cooldown window and go straight to the
                      fallback — avoids piling up slow, doomed requests
                      when NWS is down.
  - cache:           successful responses are cached in-memory, keyed by
                      lat/lng rounded to ~1km, for a few minutes. Fine for
                      a single-process portfolio demo; a real multi-worker
                      deployment would use Redis instead (PRD's own tech
                      stack section notes this as optional infra).
  - fallback:        if NWS is unreachable (or the circuit is open), return
                      a clearly-marked placeholder rather than a 500 — the
                      map/recommendation pages must still render (PRD §17).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from app.core.config import get_settings

NWS_BASE_URL = "https://api.weather.gov"
REQUEST_TIMEOUT_SECONDS = 5.0
RETRY_DELAY_SECONDS = 0.5
CACHE_TTL_SECONDS = 15 * 60  # 15 minutes — grid forecasts don't change fast
CIRCUIT_FAILURE_THRESHOLD = 3
CIRCUIT_COOLDOWN_SECONDS = 60


@dataclass(frozen=True)
class CurrentConditions:
    temperature: float | None
    temperature_unit: str
    wind_speed: str | None
    wind_direction: str | None
    short_forecast: str
    is_daytime: bool


@dataclass(frozen=True)
class HourlyPeriod:
    start_time: datetime
    temperature: float | None
    temperature_unit: str
    wind_speed: str | None
    wind_direction: str | None
    short_forecast: str
    probability_of_precipitation: int | None


@dataclass(frozen=True)
class WeatherAlert:
    event: str
    severity: str
    headline: str | None
    effective: datetime | None
    expires: datetime | None


@dataclass(frozen=True)
class WeatherSnapshot:
    latitude: float
    longitude: float
    current: CurrentConditions
    hourly: list[HourlyPeriod]
    alerts: list[WeatherAlert]
    source: str  # "nws" | "fallback"
    stale: bool
    fetched_at: datetime


class _CircuitBreaker:
    """Minimal consecutive-failure circuit breaker, same in-memory-singleton
    shape as app/services/tpwd_refresh_job.py's job tracker — appropriate
    for a single-process demo, not a substitute for a real resilience
    library in a multi-worker deployment."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._consecutive_failures = 0
        self._opened_at: float | None = None

    def is_open(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return False
            if time.monotonic() - self._opened_at >= CIRCUIT_COOLDOWN_SECONDS:
                # Cooldown elapsed — allow one probe call through.
                self._opened_at = None
                self._consecutive_failures = 0
                return False
            return True

    def record_success(self) -> None:
        with self._lock:
            self._consecutive_failures = 0
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self._consecutive_failures += 1
            if self._consecutive_failures >= CIRCUIT_FAILURE_THRESHOLD:
                self._opened_at = time.monotonic()


@dataclass
class _CacheEntry:
    snapshot: WeatherSnapshot
    cached_at: float = field(default_factory=time.monotonic)

    def is_fresh(self) -> bool:
        return time.monotonic() - self.cached_at < CACHE_TTL_SECONDS


_circuit = _CircuitBreaker()
_cache: dict[tuple[float, float], _CacheEntry] = {}
_cache_lock = threading.Lock()


def _cache_key(lat: float, lng: float) -> tuple[float, float]:
    # ~1km grid — NWS forecasts are per-gridpoint anyway, so rounding this
    # tightly buys nothing and just fragments the cache.
    return round(lat, 2), round(lng, 2)


def _get_with_retry(client: httpx.Client, url: str) -> dict:
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            last_exc = exc
            if attempt == 0:
                time.sleep(RETRY_DELAY_SECONDS)
    assert last_exc is not None
    raise last_exc


def _parse_period(period: dict) -> HourlyPeriod:
    return HourlyPeriod(
        start_time=datetime.fromisoformat(period["startTime"]),
        temperature=period.get("temperature"),
        temperature_unit=period.get("temperatureUnit", "F"),
        wind_speed=period.get("windSpeed"),
        wind_direction=period.get("windDirection"),
        short_forecast=period.get("shortForecast", ""),
        probability_of_precipitation=(
            (period.get("probabilityOfPrecipitation") or {}).get("value")
        ),
    )


def _fetch_live(lat: float, lng: float) -> WeatherSnapshot:
    settings = get_settings()
    headers = {"User-Agent": settings.nws_user_agent, "Accept": "application/geo+json"}
    # The /points/ endpoint 404s on more than 4 decimal places of precision —
    # a real NWS API constraint, not a style choice. A coordinate read back
    # from a float DB column or computed from a map click routinely carries
    # more digits than that (e.g. 32.806499999999996), so this must be
    # rounded here rather than trusted to already be clean.
    lat_r, lng_r = round(lat, 4), round(lng, 4)
    with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, headers=headers) as client:
        points = _get_with_retry(client, f"{NWS_BASE_URL}/points/{lat_r},{lng_r}")
        props = points["properties"]

        forecast_hourly = _get_with_retry(client, props["forecastHourly"])
        hourly_periods_raw = forecast_hourly["properties"]["periods"]
        hourly = [_parse_period(p) for p in hourly_periods_raw[:24]]

        current_raw = hourly_periods_raw[0] if hourly_periods_raw else None
        if current_raw is not None:
            current = CurrentConditions(
                temperature=current_raw.get("temperature"),
                temperature_unit=current_raw.get("temperatureUnit", "F"),
                wind_speed=current_raw.get("windSpeed"),
                wind_direction=current_raw.get("windDirection"),
                short_forecast=current_raw.get("shortForecast", ""),
                is_daytime=bool(current_raw.get("isDaytime", True)),
            )
        else:
            current = _fallback_current()

        alerts_raw = _get_with_retry(
            client, f"{NWS_BASE_URL}/alerts/active?point={lat_r},{lng_r}"
        )
        alerts = [
            WeatherAlert(
                event=f["properties"].get("event", "Alert"),
                severity=f["properties"].get("severity", "Unknown"),
                headline=f["properties"].get("headline"),
                effective=(
                    datetime.fromisoformat(f["properties"]["effective"])
                    if f["properties"].get("effective")
                    else None
                ),
                expires=(
                    datetime.fromisoformat(f["properties"]["expires"])
                    if f["properties"].get("expires")
                    else None
                ),
            )
            for f in alerts_raw.get("features", [])
        ]

    return WeatherSnapshot(
        latitude=lat,
        longitude=lng,
        current=current,
        hourly=hourly,
        alerts=alerts,
        source="nws",
        stale=False,
        fetched_at=datetime.now(timezone.utc),
    )


def _fallback_current() -> CurrentConditions:
    return CurrentConditions(
        temperature=None,
        temperature_unit="F",
        wind_speed=None,
        wind_direction=None,
        short_forecast="Weather data temporarily unavailable",
        is_daytime=True,
    )


def _fallback_snapshot(lat: float, lng: float) -> WeatherSnapshot:
    """A fixed-template fallback (PRD §17): recommendations built on top of
    this must not claim a species-match/weather bonus for information we
    don't actually have — the caller checks `source == "fallback"` and
    should treat weather as an unknown factor, not a favorable one."""
    return WeatherSnapshot(
        latitude=lat,
        longitude=lng,
        current=_fallback_current(),
        hourly=[],
        alerts=[],
        source="fallback",
        stale=True,
        fetched_at=datetime.now(timezone.utc),
    )


def get_weather(lat: float, lng: float) -> WeatherSnapshot:
    """Public entry point: cache -> circuit breaker -> live NWS call ->
    fallback, in that order. Never raises — always returns a snapshot, live
    or fallback, so callers (the API layer, and later the scoring engine)
    don't need their own try/except around every use of weather data."""
    key = _cache_key(lat, lng)

    with _cache_lock:
        cached = _cache.get(key)
        if cached is not None and cached.is_fresh():
            return cached.snapshot

    if _circuit.is_open():
        return _fallback_snapshot(lat, lng)

    try:
        snapshot = _fetch_live(lat, lng)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        _circuit.record_failure()
        print(f"weather_adapter: NWS fetch failed for ({lat}, {lng}): {exc!r}")
        return _fallback_snapshot(lat, lng)

    _circuit.record_success()
    with _cache_lock:
        _cache[key] = _CacheEntry(snapshot=snapshot)
    return snapshot


def reset_state() -> None:
    """Test/dev helper — clears the cache and circuit breaker so tests
    don't leak state into each other (same pattern as tpwd_refresh_job's
    reset(), used via an autouse fixture)."""
    global _circuit
    with _cache_lock:
        _cache.clear()
    _circuit = _CircuitBreaker()
