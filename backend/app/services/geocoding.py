"""Free-text place search ("Lake Fork, TX" -> coordinates), via
OpenStreetMap's Nominatim. See docs/adr/0009-geocoding.md for the full
reasoning; the short version:

Same PRD §17 reliability shape as weather_adapter.py — timeout, retry,
circuit breaker, cache, fallback — with two differences driven by
Nominatim's own usage policy
(https://operations.osmfoundation.org/policies/nominatim/):

  - **Never called from the browser.** The policy explicitly singles out
    "distributed apps" — many independent clients each hitting the public
    endpoint — as the thing it disallows; it wants "light, user-initiated
    queries", not a service fronting an app's whole user base. Routing
    every request through this one backend process, with the cache below,
    is what keeps a many-user app inside that "light usage" shape: the
    request volume this module actually sends depends on how many *distinct*
    place names get searched, not how many users are searching them.
  - **An explicit outgoing rate limit** (`_throttle`, min 1 second between
    live Nominatim calls, process-wide) — not a courtesy, the policy's
    stated hard cap.
  - **No fabricated fallback.** Weather's fallback returns a clearly-marked
    placeholder snapshot because "conditions unknown" is itself a valid
    thing to score against. There's no equivalent honest placeholder for
    "where is this place" — making up coordinates would be exactly the kind
    of fabrication this project's whole design (ai_advisor.py, the TPWD
    scraper) refuses to do elsewhere. So an outage raises
    `GeocodingUnavailable` instead of returning a fake result, and the API
    layer turns that into a 503 that's honest about being a service issue
    — distinct from a 404, which means "checked, no such place".
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

import httpx

from app.core.config import get_settings

NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"
REQUEST_TIMEOUT_SECONDS = 5.0
RETRY_DELAY_SECONDS = 0.5
# A place's coordinates don't go stale the way a weather forecast does, so
# this cache is long-lived rather than minutes — see the module docstring
# for why a long TTL here is also what keeps this compliant with Nominatim's
# "cache results" requirement rather than just a nice-to-have.
CACHE_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days
CIRCUIT_FAILURE_THRESHOLD = 3
CIRCUIT_COOLDOWN_SECONDS = 60
MIN_SECONDS_BETWEEN_LIVE_REQUESTS = 1.0  # Nominatim's own stated hard cap


class GeocodingUnavailable(Exception):
    """Nominatim is down or the circuit is open — distinct from "no match
    found" (search worked, this place doesn't exist). Conflating the two
    would tell someone "no such place" when the truth is "couldn't check
    right now", which is a worse and more misleading answer to give someone
    trying to find a lake."""


@dataclass(frozen=True)
class GeocodeResult:
    query: str
    display_name: str
    latitude: float
    longitude: float
    source: str = "nominatim"


class _CircuitBreaker:
    """Same in-memory-singleton shape as weather_adapter.py's — appropriate
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
    # None is a cached result too: a typo'd query that Nominatim genuinely
    # has no match for shouldn't re-hit the live service every time someone
    # (or the same someone, retrying) searches it again.
    result: GeocodeResult | None
    cached_at: float = field(default_factory=time.monotonic)

    def is_fresh(self) -> bool:
        return time.monotonic() - self.cached_at < CACHE_TTL_SECONDS


_circuit = _CircuitBreaker()
_cache: dict[str, _CacheEntry] = {}
_cache_lock = threading.Lock()
_rate_lock = threading.Lock()
_last_request_at = 0.0


def _normalize_query(query: str) -> str:
    return " ".join(query.strip().lower().split())


def _throttle() -> None:
    """Blocks until at least MIN_SECONDS_BETWEEN_LIVE_REQUESTS has passed
    since the last live call this process made — process-wide, not
    per-caller, matching Nominatim's own per-source (not per-user) cap."""
    global _last_request_at
    with _rate_lock:
        wait = MIN_SECONDS_BETWEEN_LIVE_REQUESTS - (time.monotonic() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.monotonic()


def _fetch_live(query: str) -> GeocodeResult | None:
    settings = get_settings()
    headers = {"User-Agent": settings.nominatim_user_agent, "Accept-Language": "en"}
    params: dict[str, str | int] = {
        "q": query,
        "format": "jsonv2",
        "limit": 1,
        # PRD scope is US freshwater fishing for beginners — narrowing here
        # both matches that scope and avoids an ambiguous match landing on
        # a same-named place on the wrong continent.
        "countrycodes": "us",
    }

    last_exc: Exception | None = None
    results: list[dict] | None = None
    for attempt in range(2):
        _throttle()
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, headers=headers) as client:
                resp = client.get(f"{NOMINATIM_BASE_URL}/search", params=params)
                resp.raise_for_status()
                results = resp.json()
            break
        except (httpx.HTTPError, ValueError) as exc:
            last_exc = exc
            if attempt == 0:
                time.sleep(RETRY_DELAY_SECONDS)
    if results is None:
        assert last_exc is not None
        raise last_exc

    if not results:
        return None
    top = results[0]
    return GeocodeResult(
        query=query,
        display_name=top.get("display_name", query),
        latitude=float(top["lat"]),
        longitude=float(top["lon"]),
    )


def geocode(query: str) -> GeocodeResult | None:
    """Public entry point: cache -> circuit breaker -> live Nominatim call.

    Returns None for "searched, no such place" — a real answer. Raises
    GeocodingUnavailable for "couldn't check" (service down or circuit
    open) — callers must not treat the two the same way (see the module
    docstring and GeocodingUnavailable's own docstring)."""
    key = _normalize_query(query)
    if not key:
        return None

    with _cache_lock:
        cached = _cache.get(key)
        if cached is not None and cached.is_fresh():
            return cached.result

    if _circuit.is_open():
        raise GeocodingUnavailable("geocoding service is temporarily unavailable")

    try:
        result = _fetch_live(query)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        _circuit.record_failure()
        print(f"geocoding: Nominatim lookup failed for {query!r}: {exc!r}")
        raise GeocodingUnavailable("geocoding service is temporarily unavailable") from exc

    _circuit.record_success()
    with _cache_lock:
        _cache[key] = _CacheEntry(result=result)
    return result


def reset_state() -> None:
    """Test/dev helper — same pattern as weather_adapter.reset_state()."""
    global _circuit, _last_request_at
    with _cache_lock:
        _cache.clear()
    _circuit = _CircuitBreaker()
    _last_request_at = 0.0
