"""Accounts, sessions and Google sign-in (Google's endpoints are faked)."""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import token_digest
from app.models.community import CatchPin, User, UserSession
from tests.conftest import make_admin, signup

PW = "tight-lines-42"


def test_register_signs_you_in_with_a_hardened_cookie(make_client):
    c = make_client()
    resp = c.post("/api/auth/register", json={"email": " Angler@Example.com ", "password": PW, "display_name": "  Big   Al "})
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "angler@example.com"
    assert body["display_name"] == "Big Al"
    assert body["role"] == "user" and body["has_password"] and not body["google_connected"]
    cookie = resp.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie
    assert c.get("/api/auth/me").json()["email"] == "angler@example.com"


def test_session_endpoint_answers_signed_out_without_an_error(make_client):
    c = make_client()
    assert c.get("/api/auth/session").json() == {"user": None}
    signup(c)
    body = c.get("/api/auth/session").json()
    assert body["user"]["email"] == "angler@example.com"


def test_only_a_digest_of_the_session_token_is_stored(make_client, db_session):
    c = make_client()
    signup(c)
    token = c.cookies.get(get_settings().session_cookie_name)
    stored = db_session.scalars(select(UserSession.token_hash)).all()
    assert token not in stored
    assert token_digest(token) in stored


@pytest.mark.parametrize(
    "payload, status",
    [
        ({"email": "not-an-email", "password": PW, "display_name": "Al"}, 422),
        ({"email": "a@b.co", "password": "short", "display_name": "Al"}, 422),
        ({"email": "a@b.co", "password": "password123", "display_name": "Al"}, 422),
        ({"email": "a@b.co", "password": PW, "display_name": "A"}, 422),
        ({"email": "a@b.co", "password": PW, "display_name": "Al‮ice"}, 422),
    ],
)
def test_register_validation(make_client, payload, status):
    assert make_client().post("/api/auth/register", json=payload).status_code == status


def test_duplicate_email_is_refused_case_insensitively(make_client):
    signup(make_client())
    resp = make_client().post("/api/auth/register", json={"email": "ANGLER@example.com", "password": PW, "display_name": "Two"})
    assert resp.status_code == 409


def test_login_failures_look_the_same_for_unknown_email_and_wrong_password(make_client):
    signup(make_client())
    c = make_client()
    wrong = c.post("/api/auth/login", json={"email": "angler@example.com", "password": "nope-nope-nope"})
    unknown = c.post("/api/auth/login", json={"email": "nobody@example.com", "password": "nope-nope-nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    ok = c.post("/api/auth/login", json={"email": "Angler@example.com", "password": PW})
    assert ok.status_code == 200 and c.get("/api/auth/me").status_code == 200


def test_repeated_failures_are_rate_limited_per_email(make_client):
    signup(make_client())
    c = make_client()
    for _ in range(8):
        assert c.post("/api/auth/login", json={"email": "angler@example.com", "password": "wrong-wrong"}).status_code == 401
    blocked = c.post("/api/auth/login", json={"email": "angler@example.com", "password": PW})
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0


def test_logout_ends_the_session_server_side(make_client):
    c = make_client()
    signup(c)
    token = c.cookies.get(get_settings().session_cookie_name)
    assert c.post("/api/auth/logout").status_code == 204
    # Even a copy of the old cookie no longer works.
    thief = make_client()
    thief.cookies.set(get_settings().session_cookie_name, token)
    assert thief.get("/api/auth/me").status_code == 401


def test_changing_password_signs_out_other_sessions_but_not_this_one(make_client):
    a = make_client()
    signup(a)
    b = make_client()
    b.post("/api/auth/login", json={"email": "angler@example.com", "password": PW})
    assert b.get("/api/auth/me").status_code == 200

    bad = a.post("/api/auth/me/password", json={"current_password": "wrong-one!", "new_password": "new-lines-99"})
    assert bad.status_code == 403
    ok = a.post("/api/auth/me/password", json={"current_password": PW, "new_password": "new-lines-99"})
    assert ok.status_code == 200
    assert a.get("/api/auth/me").status_code == 200
    assert b.get("/api/auth/me").status_code == 401
    assert make_client().post("/api/auth/login", json={"email": "angler@example.com", "password": "new-lines-99"}).status_code == 200


def test_profile_update(make_client):
    c = make_client()
    signup(c)
    assert c.patch("/api/auth/me", json={"display_name": "Crappie Queen"}).json()["display_name"] == "Crappie Queen"
    assert c.patch("/api/auth/me", json={"display_name": "x"}).status_code == 422


def test_cross_site_writes_are_refused(make_client):
    c = make_client()
    resp = c.post(
        "/api/auth/register",
        json={"email": "a@b.co", "password": PW, "display_name": "Al"},
        headers={"Origin": "https://evil.example"},
    )
    assert resp.status_code == 403
    ok = c.post(
        "/api/auth/register",
        json={"email": "a@b.co", "password": PW, "display_name": "Al"},
        headers={"Origin": get_settings().frontend_origin},
    )
    assert ok.status_code == 201


def test_deleting_your_account_removes_your_pins(make_client, db_session):
    c = make_client()
    signup(c)
    c.post("/api/pins", data={"latitude": 32.8, "longitude": -95.6, "title": "Dock"})
    assert c.request("DELETE", "/api/auth/me", json={"password": "wrong-wrong"}).status_code == 403
    assert c.request("DELETE", "/api/auth/me", json={"password": PW}).status_code == 204
    assert db_session.scalar(select(User)) is None
    assert db_session.scalar(select(CatchPin)) is None
    assert c.get("/api/auth/me").status_code == 401


def test_the_last_admin_cant_delete_themselves(make_client, db_session):
    c = make_client()
    signup(c)
    make_admin(db_session, "angler@example.com")
    assert c.request("DELETE", "/api/auth/me", json={"password": PW}).status_code == 409


def test_suspension_ends_existing_sessions_and_blocks_login(make_client, db_session):
    c = make_client()
    signup(c)
    user = db_session.scalar(select(User))
    user.status = "suspended"
    db_session.commit()
    assert c.get("/api/auth/me").status_code == 401
    resp = make_client().post("/api/auth/login", json={"email": "angler@example.com", "password": PW})
    assert resp.status_code == 403


# --------------------------------------------------------------- Google


@pytest.fixture()
def google_on(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "google_client_id", "cid.apps.googleusercontent.com")
    monkeypatch.setattr(s, "google_client_secret", "shh")


_REAL_POST, _REAL_GET = httpx.Client.post, httpx.Client.get


def _fake_google(monkeypatch, profile: dict):
    calls = {}

    def post(self, url, *a, **kw):
        if "oauth2.googleapis.com" not in str(url):
            return _REAL_POST(self, url, *a, **kw)
        calls["token_form"] = kw["data"]
        return httpx.Response(200, json={"access_token": "at"}, request=httpx.Request("POST", str(url)))

    def get(self, url, *a, **kw):
        if "googleapis.com" not in str(url):
            return _REAL_GET(self, url, *a, **kw)
        return httpx.Response(200, json=profile, request=httpx.Request("GET", str(url)))

    monkeypatch.setattr(httpx.Client, "post", post)
    monkeypatch.setattr(httpx.Client, "get", get)
    return calls


def _start(c) -> tuple[str, str]:
    resp = c.get("/api/auth/google/start?next=/community", follow_redirects=False)
    assert resp.status_code == 302
    q = parse_qs(urlparse(resp.headers["location"]).query)
    assert q["code_challenge_method"] == ["S256"] and q["scope"] == ["openid email profile"]
    return q["state"][0], q["redirect_uri"][0]


def test_providers_reports_google_only_when_configured(make_client, monkeypatch):
    assert make_client().get("/api/auth/providers").json() == {"password": True, "google": False}
    assert make_client().get("/api/auth/google/start", follow_redirects=False).status_code == 404


def test_google_sign_in_creates_an_account_and_returns_to_the_app(make_client, google_on, monkeypatch, db_session):
    calls = _fake_google(monkeypatch, {"sub": "g-1", "email": "New@Gmail.com", "email_verified": True, "name": "New Angler"})
    c = make_client()
    state, redirect_uri = _start(c)
    assert redirect_uri.endswith("/api/auth/google/callback")
    resp = c.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == f"{get_settings().frontend_origin}/community"
    assert calls["token_form"]["code_verifier"]  # PKCE verifier sent back
    me = c.get("/api/auth/me").json()
    assert me["email"] == "new@gmail.com" and me["google_connected"] and not me["has_password"]


def test_google_state_mismatch_is_refused(make_client, google_on, monkeypatch):
    _fake_google(monkeypatch, {"sub": "g-1", "email": "a@gmail.com", "email_verified": True})
    c = make_client()
    _start(c)
    resp = c.get("/api/auth/google/callback?code=abc&state=forged", follow_redirects=False)
    assert "error=google_state" in resp.headers["location"]
    assert c.get("/api/auth/me").status_code == 401


def test_google_never_silently_takes_over_a_password_account(make_client, google_on, monkeypatch):
    signup(make_client(), email="angler@example.com")
    _fake_google(monkeypatch, {"sub": "g-2", "email": "angler@example.com", "email_verified": True})
    c = make_client()
    state, _ = _start(c)
    resp = c.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert "error=google_email_exists" in resp.headers["location"]
    assert c.get("/api/auth/me").status_code == 401


def test_signed_in_users_can_connect_google_and_then_use_it(make_client, google_on, monkeypatch):
    c = make_client()
    signup(c)
    _fake_google(monkeypatch, {"sub": "g-3", "email": "other@gmail.com", "email_verified": True})
    state, _ = _start(c)
    resp = c.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert "connected=google" in resp.headers["location"]
    assert c.get("/api/auth/me").json()["google_connected"]
    fresh = make_client()
    state, _ = _start(fresh)
    fresh.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert fresh.get("/api/auth/me").json()["email"] == "angler@example.com"


def test_unverified_google_email_is_refused(make_client, google_on, monkeypatch):
    _fake_google(monkeypatch, {"sub": "g-4", "email": "x@gmail.com", "email_verified": False})
    c = make_client()
    state, _ = _start(c)
    resp = c.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert "error=google_unverified" in resp.headers["location"]


def test_google_only_accounts_must_set_a_password_before_disconnecting(make_client, google_on, monkeypatch):
    _fake_google(monkeypatch, {"sub": "g-5", "email": "g@gmail.com", "email_verified": True, "name": "G"})
    c = make_client()
    state, _ = _start(c)
    c.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert c.post("/api/auth/me/google/disconnect").status_code == 409
    assert c.post("/api/auth/me/password", json={"new_password": "first-pass-77"}).status_code == 200
    assert c.post("/api/auth/me/google/disconnect").json()["google_connected"] is False


@pytest.mark.parametrize("nxt", ["https://evil.example", "//evil.example", "/\\evil"])
def test_oauth_return_path_cannot_be_an_open_redirect(make_client, google_on, monkeypatch, nxt):
    _fake_google(monkeypatch, {"sub": "g-6", "email": "h@gmail.com", "email_verified": True})
    c = make_client()
    resp = c.get("/api/auth/google/start", params={"next": nxt}, follow_redirects=False)
    state = parse_qs(urlparse(resp.headers["location"]).query)["state"][0]
    back = c.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert back.headers["location"] == f"{get_settings().frontend_origin}/account"
