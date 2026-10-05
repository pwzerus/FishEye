"""Regression tests for the security review of accounts and community pins:
stale-session re-authentication, dangling references after account
deletion, request-size caps, bounded ids, and the smaller fixes."""
from __future__ import annotations

import io
import json
from datetime import timedelta

import pytest
from PIL import Image
from sqlalchemy import select, text

from app.api.auth import _safe_next
from app.core.security import RateLimiter
from app.db.types import utcnow
from app.models.community import User, UserSession
from tests.conftest import make_admin, signup
from tests.test_auth_api import PW, _fake_google, _start, google_on  # noqa: F401  (fixture)
from tests.test_pins_api import create, jpeg


def _age_sessions(db_session, email: str, minutes: int = 60) -> None:
    """Make every session of `email` look `minutes` old."""
    user = db_session.scalar(select(User).where(User.email == email))
    for s in user.sessions:
        s.created_at = utcnow() - timedelta(minutes=minutes)
    db_session.commit()


def _google_account(make_client, monkeypatch, sub="g-9", email="g9@gmail.com"):
    _fake_google(monkeypatch, {"sub": sub, "email": email, "email_verified": True, "name": "G Nine"})
    c = make_client()
    state, _ = _start(c)
    c.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert c.get("/api/auth/me").json()["email"] == email
    return c


# ------------------------------------------------------- re-authentication


def test_a_stale_session_must_reconfirm_the_password_before_disconnecting_google(
    make_client, google_on, monkeypatch, db_session  # noqa: F811
):
    c = make_client()
    signup(c)
    _fake_google(monkeypatch, {"sub": "g-7", "email": "other@gmail.com", "email_verified": True})
    state, _ = _start(c)
    c.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    _age_sessions(db_session, "angler@example.com")

    stale = c.post("/api/auth/me/google/disconnect")
    assert stale.status_code == 403 and stale.headers["x-reauth-required"] == "1"

    wrong = c.post("/api/auth/reauth", json={"password": "not-my-password"})
    assert wrong.status_code == 403 and "x-reauth-required" not in wrong.headers

    old_cookie = c.cookies.get("fm_session")
    assert c.post("/api/auth/reauth", json={"password": PW}).status_code == 200
    assert c.cookies.get("fm_session") != old_cookie  # a new session, not the old one refreshed
    assert c.post("/api/auth/me/google/disconnect").json()["google_connected"] is False

    revoked = db_session.scalars(select(UserSession).where(UserSession.revoked_at.is_not(None))).all()
    assert len(revoked) == 1


def test_reauth_attempts_are_rate_limited(make_client):
    c = make_client()
    signup(c)
    for _ in range(8):
        c.post("/api/auth/reauth", json={"password": "wrong-guess-00"})
    assert c.post("/api/auth/reauth", json={"password": PW}).status_code == 429


def test_google_only_accounts_reconfirm_with_google(make_client, google_on, monkeypatch, db_session):  # noqa: F811
    c = _google_account(make_client, monkeypatch)
    _age_sessions(db_session, "g9@gmail.com")

    first_password = c.post("/api/auth/me/password", json={"new_password": "first-pass-77"})
    assert first_password.status_code == 403 and first_password.headers["x-reauth-required"] == "1"
    delete = c.request("DELETE", "/api/auth/me", json={})
    assert delete.status_code == 403 and delete.headers["x-reauth-required"] == "1"

    # Signing in with the same Google account again is the re-confirmation:
    # it replaces the stale session with a fresh one.
    state, _ = _start(c)
    back = c.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert "error" not in back.headers["location"]
    assert c.post("/api/auth/me/password", json={"new_password": "first-pass-77"}).status_code == 200
    assert len(db_session.scalar(select(User).where(User.email == "g9@gmail.com")).sessions) == 2  # old one revoked, kept


def test_a_stale_session_cannot_connect_a_new_google_account(make_client, google_on, monkeypatch, db_session):  # noqa: F811
    c = make_client()
    signup(c)
    _age_sessions(db_session, "angler@example.com")
    _fake_google(monkeypatch, {"sub": "attacker", "email": "attacker@gmail.com", "email_verified": True})
    state, _ = _start(c)
    back = c.get(f"/api/auth/google/callback?code=abc&state={state}", follow_redirects=False)
    assert back.headers["location"].endswith("/account?error=reauth_required")
    assert c.get("/api/auth/me").json()["google_connected"] is False


def test_password_accounts_confirm_deletion_with_the_password_even_when_stale(make_client, db_session):
    c = make_client()
    signup(c)
    _age_sessions(db_session, "angler@example.com")
    assert c.request("DELETE", "/api/auth/me", json={"password": "nope-nope-nope"}).status_code == 403
    assert c.request("DELETE", "/api/auth/me", json={"password": PW}).status_code == 204


# ------------------------------------------------------------ OAuth input


@pytest.mark.parametrize("nxt", ["/a|b", "/tab\there", "/new\nline", "/café", "/" + "x" * 250, "", None])
def test_return_paths_must_be_plain_short_relative_ascii(nxt):
    assert _safe_next(nxt) == "/account"


def test_return_paths_that_are_fine_pass_through():
    assert _safe_next("/community/12?x=1") == "/community/12?x=1"


def test_a_non_ascii_state_is_refused_not_a_crash(make_client, google_on, monkeypatch):  # noqa: F811
    _fake_google(monkeypatch, {"sub": "g-1", "email": "a@gmail.com", "email_verified": True})
    c = make_client()
    _start(c)
    resp = c.get("/api/auth/google/callback", params={"code": "abc", "state": "café"}, follow_redirects=False)
    assert resp.status_code == 302 and "error=google_state" in resp.headers["location"]


# ------------------------------------------- deleted accounts leave no holes


def test_reports_survive_the_reporter_deleting_their_account(make_client, db_session):
    owner = make_client()
    signup(owner)
    pin = create(owner).json()
    reporter = make_client()
    signup(reporter, email="reporter@example.com", name="Reporter")
    assert reporter.post(f"/api/pins/{pin['id']}/reports", json={"reason": "spam"}).status_code == 201
    assert reporter.request("DELETE", "/api/auth/me", json={"password": PW}).status_code == 204

    admin = make_client()
    signup(admin, email="admin@example.com", name="Admin")
    make_admin(db_session, "admin@example.com")
    queue = admin.get("/api/admin/reports")
    assert queue.status_code == 200
    assert queue.json()[0]["reports"][0]["reporter"] == "Deleted account"
    assert admin.post(f"/api/admin/reports/{pin['id']}/resolve", json={"action": "dismiss"}).status_code == 200


def test_the_audit_log_still_names_an_actor_whose_account_is_gone(make_client, db_session):
    owner = make_client()
    signup(owner)
    pin = create(owner).json()
    first, second = make_client(), make_client()
    signup(first, email="first@example.com", name="First Admin")
    signup(second, email="second@example.com", name="Second Admin")
    make_admin(db_session, "first@example.com")
    make_admin(db_session, "second@example.com")

    assert first.post(f"/api/admin/pins/{pin['id']}/status", json={"status": "hidden"}).status_code == 200
    assert first.request("DELETE", "/api/auth/me", json={"password": PW}).status_code == 204

    items = second.get("/api/admin/audit").json()["items"]
    actions = {i["action"]: i for i in items}
    assert actions["user.deleted"]["actor"] == "First Admin <first@example.com> (deleted)"
    assert actions["pin.hidden"]["actor"] == "First Admin <first@example.com> (deleted)"


def test_ids_are_never_handed_out_twice(make_client):
    c = make_client()
    signup(c)
    first = create(c).json()["id"]
    assert c.delete(f"/api/pins/{first}").status_code == 204
    assert create(c).json()["id"] > first


def test_sqlite_enforces_foreign_keys(db_session):
    # PRAGMA is SQLite's own dialect, and the opt-in it checks only exists
    # there — PostgreSQL enforces foreign keys unconditionally. Skipping
    # keeps this suite runnable against the deployment database
    # (TEST_DATABASE_URL, see conftest.py) instead of failing on a
    # question that database doesn't have to be asked.
    if db_session.get_bind().dialect.name != "sqlite":
        pytest.skip("PRAGMA foreign_keys is SQLite-only; Postgres always enforces them")
    assert db_session.execute(text("PRAGMA foreign_keys")).scalar() == 1


# ------------------------------------------------------------- pin rules


def test_owners_cannot_delete_a_pin_a_moderator_took_down(make_client, db_session):
    owner = make_client()
    signup(owner)
    pin = create(owner).json()
    admin = make_client()
    signup(admin, email="admin@example.com", name="Admin")
    make_admin(db_session, "admin@example.com")
    admin.post(f"/api/admin/pins/{pin['id']}/status", json={"status": "hidden"})

    resp = owner.delete(f"/api/pins/{pin['id']}")
    assert resp.status_code == 409  # the evidence stays until a moderator decides
    assert owner.get(f"/api/pins/{pin['id']}").json()["can_edit"] is False
    assert owner.patch(f"/api/pins/{pin['id']}", json={"title": "Nothing to see"}).status_code == 409
    admin.post(f"/api/admin/pins/{pin['id']}/status", json={"status": "published"})
    assert owner.delete(f"/api/pins/{pin['id']}").status_code == 204


def test_deleting_a_reported_pin_is_audited(make_client, db_session):
    owner = make_client()
    signup(owner)
    pin = create(owner).json()
    reporter = make_client()
    signup(reporter, email="reporter@example.com", name="Reporter")
    reporter.post(f"/api/pins/{pin['id']}/reports", json={"reason": "spam"})
    assert owner.delete(f"/api/pins/{pin['id']}").status_code == 204
    from app.models.community import AuditLog

    entry = db_session.scalar(select(AuditLog).where(AuditLog.action == "pin.deleted_by_owner"))
    assert entry is not None and json.loads(entry.detail)["open_reports"] == 1


@pytest.mark.parametrize("pin_id", ["0", "-1", "99999999999999999999999"])
def test_out_of_range_ids_are_422_not_500(make_client, pin_id):
    c = make_client()
    signup(c)
    assert c.get(f"/api/pins/{pin_id}").status_code == 422
    assert c.get(f"/api/media/photos/{pin_id}").status_code == 422
    assert c.delete(f"/api/pins/1/photos/{pin_id}").status_code == 422


# ------------------------------------------------------------- photos


def _mpo() -> bytes:
    """The multi-picture JPEG many phones write (Pillow reports it as MPO)."""
    out = io.BytesIO()
    first = Image.new("RGB", (800, 600), "navy")
    first.save(out, format="MPO", save_all=True, append_images=[Image.new("RGB", (800, 600), "gray")])
    data = out.getvalue()
    assert Image.open(io.BytesIO(data)).format == "MPO"
    return data


def test_phone_mpo_jpegs_are_accepted_and_flattened_to_one_frame(make_client):
    c = make_client()
    signup(c)
    pin = create(c, photos=[_mpo()])
    assert pin.status_code == 201, pin.text
    url = pin.json()["photos"][0]["url"]
    body = c.get(url[url.index("/api/"):]).content
    img = Image.open(io.BytesIO(body))
    assert img.format == "JPEG" and getattr(img, "n_frames", 1) == 1


def test_photos_are_cached_privately_only(make_client):
    c = make_client()
    signup(c)
    url = create(c, photos=[jpeg(gps=False)]).json()["photos"][0]["url"]
    resp = c.get(url[url.index("/api/"):])
    assert resp.headers["cache-control"] == "private, max-age=600"
    assert resp.headers["x-content-type-options"] == "nosniff"


# ------------------------------------------------------- request size caps


def test_oversized_bodies_are_refused_before_they_are_read(make_client):
    from app.main import MAX_OTHER_BODY, MAX_UPLOAD_BODY

    c = make_client()
    signup(c)
    big_json = c.post(
        "/api/auth/login",
        content=b"{}",
        headers={"content-type": "application/json", "content-length": str(MAX_OTHER_BODY + 1)},
    )
    assert big_json.status_code == 413
    big_upload = c.post(
        "/api/pins",
        content=b"--x--",
        headers={"content-type": "multipart/form-data; boundary=x", "content-length": str(MAX_UPLOAD_BODY + 1)},
    )
    assert big_upload.status_code == 413
    bad = c.post("/api/auth/login", content=b"{}", headers={"content-type": "application/json", "content-length": "lots"})
    assert bad.status_code == 400


def test_chunked_bodies_without_a_length_are_refused(make_client):
    c = make_client()
    signup(c)

    def chunks():
        yield b"--x\r\n"
        yield b"--x--\r\n"

    resp = c.post("/api/pins", content=chunks(), headers={"content-type": "multipart/form-data; boundary=x"})
    assert resp.status_code == 411


# ------------------------------------------------------------- limiter


def test_checking_the_limiter_never_allocates():
    limiter = RateLimiter(limit=3, window_seconds=60)
    for i in range(1000):
        assert limiter.blocked_for(f"never-seen-{i}") == 0
    assert len(limiter) == 0
    limiter.hit("a")
    assert len(limiter) == 1


def test_expired_keys_are_evicted():
    limiter = RateLimiter(limit=1, window_seconds=0.0)
    limiter.hit("a")
    assert limiter.blocked_for("a") == 0
    assert len(limiter) == 0


def test_the_frontend_can_read_the_reauth_signal_cross_origin(make_client):
    from app.core.config import get_settings

    origin = get_settings().frontend_origin.rstrip("/")
    resp = make_client().get("/api/auth/session", headers={"Origin": origin})
    exposed = resp.headers["access-control-expose-headers"].lower()
    assert "x-reauth-required" in exposed and "retry-after" in exposed
