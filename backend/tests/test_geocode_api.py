"""Tests for GET /api/geocode. Network-free — httpx.Client.get is
monkeypatched, same no-live-HTTP philosophy as test_weather_api.py."""
import httpx
import pytest

from app.services import geocoding


@pytest.fixture(autouse=True)
def _reset_geocoding_state(monkeypatch):
    geocoding.reset_state()
    # The 1-second throttle is a real requirement against the real
    # Nominatim service (see module docstring) but only adds dead time
    # against a monkeypatched one here.
    monkeypatch.setattr(geocoding, "MIN_SECONDS_BETWEEN_LIVE_REQUESTS", 0.0)
    yield
    geocoding.reset_state()


def _fake_response(payload, url: str) -> httpx.Response:
    return httpx.Response(200, json=payload, request=httpx.Request("GET", url))


_REAL_CLIENT_GET = httpx.Client.get


def _install_fake_nominatim(monkeypatch, *, results_by_query: dict[str, list[dict]] | None = None):
    """Patches httpx.Client.get to serve canned Nominatim-shaped JSON.

    Only requests to nominatim.openstreetmap.org are faked — FastAPI's own
    TestClient is itself built on httpx (talking to an in-process ASGI
    transport, not the network), so patching globally without this guard
    would also intercept the test's own request into the app."""
    results_by_query = results_by_query or {}
    call_count = {"n": 0}

    def fake_get(self, url, *args, **kwargs):
        url_str = str(url)
        if "nominatim.openstreetmap.org" not in url_str:
            return _REAL_CLIENT_GET(self, url, *args, **kwargs)
        call_count["n"] += 1
        params = kwargs.get("params") or {}
        query = params.get("q", "")
        payload = results_by_query.get(query, [])
        return _fake_response(payload, url_str)

    monkeypatch.setattr(httpx.Client, "get", fake_get)
    return call_count


LAKE_FORK_RESULT = [
    {
        "display_name": "Lake Fork Reservoir, Wood County, Texas, United States",
        "lat": "32.8065",
        "lon": "-95.5931",
    }
]


def test_a_known_place_returns_its_coordinates(client, monkeypatch):
    _install_fake_nominatim(monkeypatch, results_by_query={"Lake Fork": LAKE_FORK_RESULT})

    resp = client.get("/api/geocode", params={"q": "Lake Fork"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["latitude"] == pytest.approx(32.8065)
    assert body["longitude"] == pytest.approx(-95.5931)
    assert "Lake Fork" in body["display_name"]


def test_an_unrecognized_place_is_a_404_not_a_service_error(client, monkeypatch):
    """No match is a real, checked answer — must not be confused with the
    service being down (see geocoding.py's GeocodingUnavailable docstring)."""
    _install_fake_nominatim(monkeypatch, results_by_query={"asdkfjasldkfj": []})

    resp = client.get("/api/geocode", params={"q": "asdkfjasldkfj"})

    assert resp.status_code == 404


def test_repeated_identical_queries_hit_nominatim_only_once(client, monkeypatch):
    """The whole point of the cache (see module docstring): many callers
    asking about the same place should not scale the outgoing request
    count 1:1 with the number of askers."""
    call_count = _install_fake_nominatim(monkeypatch, results_by_query={"Lake Fork": LAKE_FORK_RESULT})

    for _ in range(5):
        resp = client.get("/api/geocode", params={"q": "Lake Fork"})
        assert resp.status_code == 200

    assert call_count["n"] == 1


def test_query_normalization_shares_the_cache_across_case_and_whitespace(client, monkeypatch):
    call_count = _install_fake_nominatim(monkeypatch, results_by_query={"Lake Fork": LAKE_FORK_RESULT})

    client.get("/api/geocode", params={"q": "Lake Fork"})
    client.get("/api/geocode", params={"q": "  LAKE   fork  "})

    assert call_count["n"] == 1


def test_a_not_found_result_is_cached_too(client, monkeypatch):
    """A typo'd query shouldn't re-hit Nominatim every time it's retried."""
    call_count = _install_fake_nominatim(monkeypatch, results_by_query={"asdkfjasldkfj": []})

    client.get("/api/geocode", params={"q": "asdkfjasldkfj"})
    client.get("/api/geocode", params={"q": "asdkfjasldkfj"})

    assert call_count["n"] == 1


def test_service_outage_is_503_not_404(client, monkeypatch):
    """A downed geocoder must not silently look like "no such place"."""

    def fake_get(self, url, *args, **kwargs):
        if "nominatim.openstreetmap.org" not in str(url):
            return _REAL_CLIENT_GET(self, url, *args, **kwargs)
        raise httpx.ConnectError("simulated outage")

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    resp = client.get("/api/geocode", params={"q": "Lake Fork"})

    assert resp.status_code == 503


def test_circuit_opens_after_repeated_failures_and_stops_calling_out(client, monkeypatch):
    call_count = {"n": 0}

    def fake_get(self, url, *args, **kwargs):
        if "nominatim.openstreetmap.org" not in str(url):
            return _REAL_CLIENT_GET(self, url, *args, **kwargs)
        call_count["n"] += 1
        raise httpx.ConnectError("simulated outage")

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    # Each failing geocode() call retries once internally, so 3 consecutive
    # geocode() calls == 6 live attempts, which trips
    # CIRCUIT_FAILURE_THRESHOLD (3) after the first call already.
    for _ in range(3):
        resp = client.get("/api/geocode", params={"q": f"nowhere-{_}"})
        assert resp.status_code == 503

    calls_before = call_count["n"]
    resp = client.get("/api/geocode", params={"q": "yet-another-nowhere"})
    assert resp.status_code == 503
    # Circuit is open: this call should not have reached the (fake) network.
    assert call_count["n"] == calls_before
