"""Tests for GET /api/weather. Network-free — httpx.Client.get is
monkeypatched, same no-live-HTTP philosophy as the TPWD scraper tests."""
from datetime import datetime, timezone

import httpx
import pytest

from app.services import weather_adapter


@pytest.fixture(autouse=True)
def _reset_weather_state():
    weather_adapter.reset_state()
    yield
    weather_adapter.reset_state()


def _fake_response(payload: dict, url: str) -> httpx.Response:
    return httpx.Response(200, json=payload, request=httpx.Request("GET", url))


_REAL_CLIENT_GET = httpx.Client.get


def _install_fake_nws(monkeypatch, *, alerts: list[dict] | None = None):
    """Patches httpx.Client.get to serve canned NWS-shaped JSON for the
    three calls get_weather makes (points -> forecastHourly -> alerts),
    keyed by URL substring rather than call order, so test intent stays
    readable.

    Only requests to api.weather.gov are faked — FastAPI's own TestClient
    is itself built on an httpx.Client (talking to an in-process ASGI
    transport, not the network), so patching httpx.Client.get globally
    without this guard would also intercept the test's own request into
    the app and break every test."""
    alerts = alerts if alerts is not None else []

    points_payload = {
        "properties": {
            "forecast": "https://api.weather.gov/gridpoints/FWD/1,1/forecast",
            "forecastHourly": "https://api.weather.gov/gridpoints/FWD/1,1/forecast/hourly",
        }
    }
    hourly_payload = {
        "properties": {
            "periods": [
                {
                    "startTime": "2026-09-22T14:00:00-05:00",
                    "temperature": 88,
                    "temperatureUnit": "F",
                    "windSpeed": "10 mph",
                    "windDirection": "SE",
                    "shortForecast": "Sunny",
                    "isDaytime": True,
                    "probabilityOfPrecipitation": {"value": 10},
                },
                {
                    "startTime": "2026-09-22T15:00:00-05:00",
                    "temperature": 89,
                    "temperatureUnit": "F",
                    "windSpeed": "12 mph",
                    "windDirection": "SE",
                    "shortForecast": "Sunny",
                    "isDaytime": True,
                    "probabilityOfPrecipitation": {"value": 5},
                },
            ]
        }
    }
    alerts_payload = {"features": alerts}

    def fake_get(self, url, *args, **kwargs):
        url_str = str(url)
        if "api.weather.gov" not in url_str:
            return _REAL_CLIENT_GET(self, url, *args, **kwargs)
        if "/points/" in url_str:
            return _fake_response(points_payload, url_str)
        if "/forecast/hourly" in url_str:
            return _fake_response(hourly_payload, url_str)
        if "/alerts/active" in url_str:
            return _fake_response(alerts_payload, url_str)
        raise AssertionError(f"unexpected URL in test: {url_str}")

    monkeypatch.setattr(httpx.Client, "get", fake_get)


def test_points_request_rounds_coordinates_to_4_decimal_places(client, monkeypatch):
    """Real NWS API constraint: /points/ 404s on more than 4 decimal places
    of precision. A coordinate read from a float DB column routinely carries
    more digits than that (e.g. 32.806499999999996), so the adapter must
    round before building the URL rather than trusting the caller's input."""
    _install_fake_nws(monkeypatch)
    seen_urls = []
    real_fake_get = httpx.Client.get

    def spy_get(self, url, *args, **kwargs):
        seen_urls.append(str(url))
        return real_fake_get(self, url, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "get", spy_get)

    resp = client.get(
        "/api/weather", params={"lat": 32.806499999999996, "lng": -95.59310000000001}
    )
    assert resp.status_code == 200

    points_call = next(u for u in seen_urls if "/points/" in u)
    assert "32.8065" in points_call
    assert "-95.5931" in points_call
    # No more than 4 digits after the decimal point in either coordinate.
    coords = points_call.rsplit("/points/", 1)[1]
    lat_str, lng_str = coords.split(",")
    assert len(lat_str.split(".")[1]) <= 4
    assert len(lng_str.split(".")[1]) <= 4


def test_weather_endpoint_returns_live_nws_data(client, monkeypatch):
    _install_fake_nws(monkeypatch)

    resp = client.get("/api/weather", params={"lat": 32.8, "lng": -96.0})
    assert resp.status_code == 200
    body = resp.json()

    assert body["source"] == "nws"
    assert body["stale"] is False
    assert body["current"]["temperature"] == 88
    assert body["current"]["short_forecast"] == "Sunny"
    assert len(body["hourly"]) == 2
    assert body["hourly"][1]["temperature"] == 89
    assert body["alerts"] == []


def test_weather_endpoint_surfaces_active_alerts(client, monkeypatch):
    _install_fake_nws(
        monkeypatch,
        alerts=[
            {
                "properties": {
                    "event": "Small Craft Advisory",
                    "severity": "Moderate",
                    "headline": "Small Craft Advisory in effect",
                    "effective": "2026-09-22T12:00:00-05:00",
                    "expires": "2026-09-22T22:00:00-05:00",
                }
            }
        ],
    )

    resp = client.get("/api/weather", params={"lat": 32.8, "lng": -96.0})
    body = resp.json()
    assert len(body["alerts"]) == 1
    assert body["alerts"][0]["event"] == "Small Craft Advisory"


def test_weather_endpoint_falls_back_when_nws_unreachable(client, monkeypatch):
    monkeypatch.setattr(weather_adapter, "RETRY_DELAY_SECONDS", 0)

    def fake_get(self, url, *args, **kwargs):
        if "api.weather.gov" not in str(url):
            return _REAL_CLIENT_GET(self, url, *args, **kwargs)
        raise httpx.ConnectError("simulated network failure")

    monkeypatch.setattr(httpx.Client, "get", fake_get)

    resp = client.get("/api/weather", params={"lat": 32.8, "lng": -96.0})
    assert resp.status_code == 200  # never a 5xx — PRD §17: core pages still work
    body = resp.json()
    assert body["source"] == "fallback"
    assert body["stale"] is True
    assert body["current"]["temperature"] is None
    assert body["hourly"] == []
    assert body["alerts"] == []


def test_weather_endpoint_uses_cache_on_second_call(client, monkeypatch):
    call_count = {"n": 0}
    _install_fake_nws(monkeypatch)
    real_fake_get = httpx.Client.get

    def counting_get(self, url, *args, **kwargs):
        if "api.weather.gov" in str(url):
            call_count["n"] += 1
        return real_fake_get(self, url, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "get", counting_get)

    client.get("/api/weather", params={"lat": 32.8, "lng": -96.0})
    first_call_count = call_count["n"]
    assert first_call_count > 0

    client.get("/api/weather", params={"lat": 32.8, "lng": -96.0})
    # A cache hit makes zero additional NWS calls.
    assert call_count["n"] == first_call_count


def test_weather_endpoint_opens_circuit_after_repeated_failures(client, monkeypatch):
    monkeypatch.setattr(weather_adapter, "RETRY_DELAY_SECONDS", 0)
    attempts = {"n": 0}

    def always_fails(self, url, *args, **kwargs):
        if "api.weather.gov" not in str(url):
            return _REAL_CLIENT_GET(self, url, *args, **kwargs)
        attempts["n"] += 1
        raise httpx.ConnectError("simulated network failure")

    monkeypatch.setattr(httpx.Client, "get", always_fails)

    # Each of these calls uses a distinct point so the cache can't mask
    # repeated live attempts, until the circuit opens.
    points = [(30.0, -95.0), (31.0, -95.0), (32.0, -95.0), (33.0, -95.0)]
    for lat, lng in points:
        resp = client.get("/api/weather", params={"lat": lat, "lng": lng})
        assert resp.json()["source"] == "fallback"

    attempts_after_all_points = attempts["n"]

    # Once the circuit is open, a brand-new point should short-circuit
    # straight to fallback without even attempting an NWS call.
    resp = client.get("/api/weather", params={"lat": 40.0, "lng": -95.0})
    assert resp.json()["source"] == "fallback"
    assert attempts["n"] == attempts_after_all_points


def test_weather_adapter_returns_snapshot_directly(monkeypatch):
    _install_fake_nws(monkeypatch)
    snapshot = weather_adapter.get_weather(32.8, -96.0)
    assert snapshot.source == "nws"
    assert snapshot.fetched_at.tzinfo is not None
    assert snapshot.fetched_at <= datetime.now(timezone.utc)
