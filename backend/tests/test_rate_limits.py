"""Request limits on the anonymous endpoints (app/api/rate_limits.py)."""
import pytest
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.api import rate_limits
from app.core import security
from app.core.config import get_settings
from app.main import app
from app.services import geocoding
from tests.conftest import make_admin, signup

QUESTION = {"question": "what bait for crappie"}


@pytest.fixture()
def as_client(monkeypatch):
    """Requests carry an `x-test-ip` header naming the client they come from.
    TestClient always connects from the same address."""
    monkeypatch.setattr(
        rate_limits, "client_ip", lambda request: request.headers.get("x-test-ip", "198.51.100.1")
    )

    def headers(ip: str) -> dict[str, str]:
        return {"x-test-ip": ip}

    return headers


def test_guide_searches_are_limited_per_client(client, as_client, monkeypatch):
    monkeypatch.setattr(rate_limits.SEARCH.per_client[0], "limit", 3)
    for _ in range(3):
        assert client.post("/api/ask", json=QUESTION, headers=as_client("a")).status_code == 200

    refused = client.post("/api/ask", json=QUESTION, headers=as_client("a"))
    assert refused.status_code == 429
    assert 1 <= int(refused.headers["Retry-After"]) <= 61
    assert "wait a moment" in refused.json()["detail"]

    # Someone else is unaffected.
    assert client.post("/api/ask", json=QUESTION, headers=as_client("b")).status_code == 200


def test_searching_the_guides_does_not_spend_the_ai_allowance(client, as_client):
    for _ in range(20):
        client.post("/api/ask", json=QUESTION, headers=as_client("a"))
    resp = client.post("/api/advisor/explain", json={"waterbody_id": 99999}, headers=as_client("a"))
    assert resp.status_code == 404  # past the limiter, to the missing lake


def explain(client, headers):
    """The advisor's model endpoint, asked about a lake that doesn't exist:
    404 means the request got past the limiter, 429 that it didn't."""
    return client.post("/api/advisor/explain", json={"waterbody_id": 99999}, headers=headers).status_code


def test_ai_summaries_and_the_advisor_share_one_allowance(make_client, as_client, db_session):
    c = make_client()
    signup(c, email="owner@example.com")
    make_admin(db_session, "owner@example.com")  # admins have no daily summary limit
    for _ in range(10):
        assert c.post("/api/ask/summary", json=QUESTION, headers=as_client("a")).status_code == 200
    assert explain(c, as_client("a")) == 429


def test_the_shared_daily_cap_stops_everyone_with_its_own_message(client, as_client, monkeypatch):
    monkeypatch.setattr(rate_limits.LLM.everyone[0], "limit", 3)
    for ip in ("a", "b", "c"):
        assert explain(client, as_client(ip)) == 404

    refused = client.post("/api/advisor/explain", json={"waterbody_id": 99999}, headers=as_client("d"))
    assert refused.status_code == 429
    assert "limit for everyone" in refused.json()["detail"]


def test_refused_requests_do_not_use_up_the_shared_cap(client, as_client, monkeypatch):
    monkeypatch.setattr(rate_limits.LLM.everyone[0], "limit", 11)
    # 10 accepted, then 5 refused for being over the client's own limit.
    statuses = [explain(client, as_client("a")) for _ in range(15)]
    assert statuses == [404] * 10 + [429] * 5
    # The refusals counted for nothing, so the 11th slot is still free.
    assert explain(client, as_client("b")) == 404


def test_location_search_is_limited(client, as_client, monkeypatch):
    monkeypatch.setattr(geocoding, "geocode", lambda q: None)
    for _ in range(20):
        assert client.get("/api/geocode?q=nowhere", headers=as_client("a")).status_code == 404
    assert client.get("/api/geocode?q=nowhere", headers=as_client("a")).status_code == 429


def test_weather_and_recommendations_share_an_allowance(client, as_client, monkeypatch):
    monkeypatch.setattr(rate_limits.WEATHER.per_client[0], "limit", 2)
    for _ in range(2):
        resp = client.post("/api/recommendations", json={"waterbody_id": 99999}, headers=as_client("a"))
        assert resp.status_code == 404
    # Refused before the weather service is ever called.
    assert client.get("/api/weather?lat=32.9&lng=-95.6", headers=as_client("a")).status_code == 429


def test_lake_queries_are_limited(client, as_client, monkeypatch):
    monkeypatch.setattr(rate_limits.MAP.per_client[0], "limit", 2)
    for _ in range(2):
        assert client.get("/api/waterbodies", headers=as_client("a")).status_code == 200
    assert client.get("/api/waterbodies", headers=as_client("a")).status_code == 429


def test_health_and_guides_are_never_limited(client, as_client):
    for _ in range(50):
        assert client.get("/health", headers=as_client("a")).status_code == 200
        assert client.get("/api/species/guides", headers=as_client("a")).status_code == 200


def test_limits_can_be_switched_off(client, as_client, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limits_enabled", False)
    for _ in range(35):
        assert client.post("/api/ask", json=QUESTION, headers=as_client("a")).status_code == 200


def test_behind_a_trusted_proxy_each_visitor_gets_their_own_allowance(client):
    """What production does: uvicorn, told to trust the proxy
    (FORWARDED_ALLOW_IPS), takes the client address from X-Forwarded-For.
    Without that, every visitor would share the proxy's address."""
    behind_proxy = TestClient(ProxyHeadersMiddleware(app, trusted_hosts="*"))

    def ask(visitor: str) -> int:
        return behind_proxy.post("/api/ask", json=QUESTION, headers={"x-forwarded-for": visitor}).status_code

    for _ in range(30):
        assert ask("203.0.113.7") == 200
    assert ask("203.0.113.7") == 429
    assert ask("203.0.113.8") == 200


def test_a_limiter_forgets_clients_that_never_come_back(monkeypatch):
    now = [0.0]
    monkeypatch.setattr(security.time, "monotonic", lambda: now[0])
    limiter = security.RateLimiter(limit=5, window_seconds=60)

    for i in range(1025):
        limiter.hit(f"old-{i}")
    now[0] = 120.0  # every old entry is now outside the window
    for i in range(1100):
        limiter.hit(f"new-{i}")

    assert len(limiter) == 1100
