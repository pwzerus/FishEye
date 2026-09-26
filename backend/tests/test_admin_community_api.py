"""Admin: dashboard, report queue, pin moderation, users, audit, CLI."""
from __future__ import annotations

import io
import json

import pytest
from sqlalchemy import select

from app.models.community import AuditLog, User
from tests.conftest import make_admin, signup
from tests.test_pins_api import create, jpeg, media_files


@pytest.fixture()
def admin(make_client, db_session):
    c = make_client()
    signup(c, email="admin@example.com", name="Admin")
    make_admin(db_session, "admin@example.com")
    return c


@pytest.fixture()
def angler(make_client):
    c = make_client()
    signup(c)
    return c


def _reported(make_client, pin_id, n, reason="spam"):
    for i in range(n):
        c = make_client()
        signup(c, email=f"r{i}@example.com", name=f"Reporter {i}")
        assert c.post(f"/api/pins/{pin_id}/reports", json={"reason": reason, "detail": f"r{i}"}).status_code == 201


@pytest.mark.parametrize(
    "method, path",
    [
        ("GET", "/api/admin/stats"),
        ("GET", "/api/admin/reports"),
        ("GET", "/api/admin/pins"),
        ("GET", "/api/admin/users"),
        ("GET", "/api/admin/audit"),
        ("PATCH", "/api/admin/users/1"),
        ("POST", "/api/admin/pins/1/status"),
    ],
)
def test_admin_endpoints_need_an_admin(make_client, angler, method, path):
    assert make_client().request(method, path, json={}).status_code == 401
    assert angler.request(method, path, json={}).status_code == 403


def test_stats(admin, angler):
    create(angler)
    create(angler, visibility="private")
    s = admin.get("/api/admin/stats").json()
    assert s["users"] == 2 and s["admins"] == 1 and s["users_new_7d"] == 2
    assert s["users_active_7d"] == 2  # signing up counts as signing in
    assert s["pins"] == 2 and s["pins_public"] == 1 and s["pins_private"] == 1
    assert s["open_reports"] == 0


def test_report_queue_groups_by_pin_most_reported_first(admin, angler, make_client):
    quiet = create(angler, title="Quiet one").json()
    loud = create(angler, title="Loud one").json()
    _reported(make_client, quiet["id"], 1)
    for i in range(2):
        c = make_client()
        signup(c, email=f"x{i}@example.com", name=f"X {i}")
        c.post(f"/api/pins/{loud['id']}/reports", json={"reason": "wrong_location"})
    queue = admin.get("/api/admin/reports").json()
    assert [g["pin"]["title"] for g in queue] == ["Loud one", "Quiet one"]
    assert queue[0]["reports"][0]["reason_label"] == "Wrong or made-up location"


def test_dismissing_reports_restores_an_auto_hidden_pin(admin, angler, make_client, db_session):
    pin = create(angler).json()
    _reported(make_client, pin["id"], 3)
    assert angler.get(f"/api/pins/{pin['id']}").json()["status"] == "hidden"

    out = admin.post(f"/api/admin/reports/{pin['id']}/resolve", json={"action": "dismiss", "note": "fine"}).json()
    assert out["status"] == "published" and out["open_reports"] == 0
    assert make_client().get(f"/api/pins/{pin['id']}").status_code == 200
    assert admin.get("/api/admin/reports").json() == []
    assert admin.post(f"/api/admin/reports/{pin['id']}/resolve", json={"action": "dismiss"}).status_code == 409
    entry = db_session.scalar(select(AuditLog).where(AuditLog.action == "reports.dismissed"))
    assert json.loads(entry.detail)["status_after"] == "published"


@pytest.mark.parametrize("action, status", [("hide", "hidden"), ("remove", "removed")])
def test_acting_on_reports(admin, angler, make_client, action, status):
    pin = create(angler).json()
    _reported(make_client, pin["id"], 1)
    out = admin.post(f"/api/admin/reports/{pin['id']}/resolve", json={"action": action}).json()
    assert out["status"] == status and out["status_reason"] == "moderator"
    assert make_client().get(f"/api/pins/{pin['id']}").status_code == 404


def test_removed_pins_are_gone_from_the_owners_map_and_locked(admin, angler):
    pin = create(angler).json()
    admin.post(f"/api/admin/pins/{pin['id']}/status", json={"status": "removed"})
    assert all(p["id"] != pin["id"] for p in angler.get("/api/pins").json())
    mine = angler.get("/api/pins", params={"mine": True}).json()
    assert mine[0]["status"] == "removed"  # still listed under "my pins", with its state
    assert angler.patch(f"/api/pins/{pin['id']}", json={"title": "Undo it"}).status_code == 409


def test_status_changes_and_restore(admin, angler, make_client):
    pin = create(angler).json()
    assert admin.post(f"/api/admin/pins/{pin['id']}/status", json={"status": "hidden"}).json()["status"] == "hidden"
    assert make_client().get(f"/api/pins/{pin['id']}").status_code == 404
    back = admin.post(f"/api/admin/pins/{pin['id']}/status", json={"status": "published"}).json()
    assert back["status"] == "published" and back["status_reason"] is None
    assert admin.post(f"/api/admin/pins/{pin['id']}/status", json={"status": "gone"}).status_code == 422


def test_admin_pin_search_and_filters(admin, angler):
    create(angler, title="Riprap bass")
    create(angler, title="Secret pond", visibility="private")
    page = admin.get("/api/admin/pins", params={"q": "riprap"}).json()
    assert page["total"] == 1 and page["items"][0]["author_email"] == "angler@example.com"
    assert admin.get("/api/admin/pins", params={"visibility": "private"}).json()["total"] == 1
    assert admin.get("/api/admin/pins", params={"q": "angler@"}).json()["total"] == 2


def test_purge_deletes_the_pin_and_its_files(admin, angler):
    pin = create(angler, photos=[jpeg(400, 300)]).json()
    assert len(media_files()) == 2
    assert admin.delete(f"/api/admin/pins/{pin['id']}").status_code == 204
    assert media_files() == []
    assert admin.get("/api/admin/audit").json()["items"][0]["action"] == "pin.purged"


def test_user_management(admin, angler, db_session):
    users = admin.get("/api/admin/users", params={"q": "angler"}).json()
    assert users["total"] == 1
    uid = users["items"][0]["id"]

    promoted = admin.patch(f"/api/admin/users/{uid}", json={"role": "admin"}).json()
    assert promoted["role"] == "admin"
    assert angler.get("/api/admin/stats").status_code == 200

    suspended = admin.patch(f"/api/admin/users/{uid}", json={"role": "user", "status": "suspended"}).json()
    assert suspended["status"] == "suspended"
    assert angler.get("/api/auth/me").status_code == 401  # sessions ended immediately
    entry = db_session.scalars(select(AuditLog).where(AuditLog.action == "user.updated")).all()[-1]
    assert json.loads(entry.detail)["sessions_revoked"] == "1"


def test_admins_cant_lock_themselves_or_the_site_out(admin, make_client, db_session):
    me = db_session.scalar(select(User).where(User.email == "admin@example.com"))
    assert admin.patch(f"/api/admin/users/{me.id}", json={"status": "suspended"}).status_code == 409

    second = make_client()
    signup(second, email="second@example.com", name="Second")
    make_admin(db_session, "second@example.com")
    # Second admin demotes the first: allowed, one admin remains.
    assert second.patch(f"/api/admin/users/{me.id}", json={"role": "user"}).status_code == 200
    # ...and now nobody can remove the last one.
    other = db_session.scalar(select(User).where(User.email == "second@example.com"))
    assert db_session.scalar(select(User).where(User.email == "admin@example.com")).role == "user"
    assert second.patch(f"/api/admin/users/{other.id}", json={"role": "user"}).status_code == 409


def test_audit_log_is_newest_first_with_actor_names(admin, angler, make_client):
    pin = create(angler).json()
    _reported(make_client, pin["id"], 3)  # system auto-hide
    admin.post(f"/api/admin/reports/{pin['id']}/resolve", json={"action": "remove"})
    items = admin.get("/api/admin/audit").json()["items"]
    assert [i["action"] for i in items[:2]] == ["reports.removed", "pin.auto_hidden"]
    assert items[0]["actor"] == "Admin" and items[1]["actor"] == "System"


def test_admin_session_can_run_the_tpwd_refresh_without_the_token(admin, angler):
    assert angler.get("/api/admin/tpwd-refresh/status").status_code in (401, 503)
    assert admin.get("/api/admin/tpwd-refresh/status").status_code == 200


# -------------------------------------------------------------------- CLI


def test_cli_creates_the_first_admin_and_promotes(monkeypatch, db_session, capsys):
    from app.cli import users as cli
    from tests.conftest import TEST_ENGINE, TestingSessionLocal

    monkeypatch.setattr(cli, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(cli, "engine", TEST_ENGINE)
    monkeypatch.setattr("sys.stdin", io.StringIO("cli-admin-pass-1\n"))
    assert cli.main(["create-admin", "--email", "Boss@Example.com", "--name", "Boss"]) == 0
    boss = db_session.scalar(select(User).where(User.email == "boss@example.com"))
    assert boss.role == "admin"

    monkeypatch.setattr("sys.stdin", io.StringIO("another-pass-1\n"))
    assert cli.main(["create-admin", "--email", "boss@example.com", "--name", "Boss"]) == 1
    assert cli.main(["demote", "--email", "boss@example.com"]) == 1  # last admin
    assert "last active admin" in capsys.readouterr().out
