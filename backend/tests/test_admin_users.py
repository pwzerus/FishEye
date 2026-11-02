"""The admin's Users screen: finding an account and acting on it."""
from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.db.types import utcnow
from app.models.community import CatchPin, User
from tests.conftest import make_admin, signup

PW = "correct horse battery staple"


@pytest.fixture
def admin(make_client, db_session):
    a = make_client()
    signup(a, email="boss@example.com", name="Head Boss")
    make_admin(db_session, "boss@example.com")
    return a


def _uid(db, email):
    return db.scalar(select(User.id).where(User.email == email))


def _someone(make_client, db, email="me@example.com", name="Some One"):
    c = make_client()
    signup(c, email=email, name=name)
    return c, _uid(db, email)


def test_the_list_counts_and_filters(admin, make_client, db_session):
    _, uid = _someone(make_client, db_session)
    _someone(make_client, db_session, "two@example.com", "Two Person")
    db_session.get(User, uid).status = "suspended"
    db_session.commit()
    body = admin.get("/api/admin/users").json()
    assert body["counts"] == {"all": 3, "admins": 1, "suspended": 1, "unconfirmed": body["counts"]["unconfirmed"], "new_7d": 3}
    assert [u["id"] for u in admin.get("/api/admin/users", params={"status": "suspended"}).json()["items"]] == [uid]
    assert [u["email"] for u in admin.get("/api/admin/users", params={"role": "admin"}).json()["items"]] == ["boss@example.com"]


def test_filter_by_unconfirmed(admin, make_client, db_session):
    _, uid = _someone(make_client, db_session)
    db_session.get(User, uid).email_verified_at = None
    db_session.commit()
    ids = [u["id"] for u in admin.get("/api/admin/users", params={"unconfirmed": True}).json()["items"]]
    assert uid in ids


@pytest.mark.parametrize("q", ["some one", "ME@EXAMPLE", "#ID", "ID"])
def test_search_by_name_address_or_number(admin, make_client, db_session, q):
    _, uid = _someone(make_client, db_session)
    q = q.replace("ID", str(uid))
    assert uid in [u["id"] for u in admin.get("/api/admin/users", params={"q": q}).json()["items"]]


@pytest.mark.parametrize("q", ["%", "_", "'", "' OR 1=1--", "99999999999999999999"])
def test_odd_searches_dont_break_or_match_everyone(admin, q):
    r = admin.get("/api/admin/users", params={"q": q})
    assert r.status_code == 200 and r.json()["items"] == []


def test_a_google_account_counts_as_confirmed(admin, make_client, db_session):
    _, uid = _someone(make_client, db_session)
    u = db_session.get(User, uid)
    u.email_verified_at, u.google_sub = None, "google-123"
    db_session.commit()
    assert admin.get(f"/api/admin/users/{uid}").json()["email_verified"] is True
    assert uid not in [x["id"] for x in admin.get("/api/admin/users", params={"unconfirmed": True}).json()["items"]]


def test_sorting(admin, make_client, db_session):
    c, busy = _someone(make_client, db_session)
    _, quiet = _someone(make_client, db_session, "two@example.com", "Two Person")
    db_session.add(CatchPin(user_id=busy, latitude=1, longitude=1, title="One", status="published", visibility="public"))
    db_session.get(User, quiet).last_login_at = utcnow() + timedelta(minutes=5)
    db_session.commit()
    first = lambda sort: admin.get("/api/admin/users", params={"sort": sort}).json()["items"][0]["id"]  # noqa: E731
    assert first("catches") == busy
    assert first("last_seen") == quiet
    assert first("newest") == quiet
    assert admin.get("/api/admin/users", params={"sort": "nope"}).status_code == 422
    assert admin.get("/api/admin/users", params={"sort": "reports"}).status_code == 200


def test_one_account_in_detail(admin, make_client, db_session):
    c, uid = _someone(make_client, db_session)
    db_session.add(CatchPin(user_id=uid, latitude=1, longitude=1, title="Mine", status="published", visibility="public"))
    db_session.add(CatchPin(user_id=uid, latitude=1, longitude=1, title="Secret", status="published", visibility="private"))
    db_session.commit()
    c.post("/api/feedback", json={"message": "hello there"})
    d = admin.get(f"/api/admin/users/{uid}").json()
    assert (d["pins"], d["pins_public"], d["pins_private"], d["feedback"]) == (2, 1, 1, 1)
    assert {p["title"] for p in d["recent_pins"]} == {"Mine", "Secret"}
    assert d["sessions"] == 1 and d["last_seen_at"]
    assert admin.get("/api/admin/users/999999").status_code == 404


def test_confirming_an_address_by_hand(admin, make_client, db_session):
    _, uid = _someone(make_client, db_session)
    db_session.get(User, uid).email_verified_at = None
    db_session.commit()
    d = admin.post(f"/api/admin/users/{uid}/confirm-email").json()
    assert d["email_verified"] is True
    assert "user.email_confirmed" in {e["action"] for e in d["history"]}


def test_signing_someone_out_everywhere(admin, make_client, db_session):
    c, uid = _someone(make_client, db_session)
    d = admin.post(f"/api/admin/users/{uid}/sign-out").json()
    assert d["sessions"] == 0 and c.get("/api/auth/me").status_code == 401
    me = _uid(db_session, "boss@example.com")
    assert admin.post(f"/api/admin/users/{me}/sign-out").status_code == 409


def test_renaming_someone(admin, make_client, db_session):
    _, uid = _someone(make_client, db_session)
    url = f"/api/admin/users/{uid}"
    assert admin.patch(url, json={"display_name": "  New  Name "}).json()["display_name"] == "New Name"
    assert admin.patch(url, json={"display_name": "nigger"}).status_code == 422
    assert admin.patch(url, json={"display_name": "Admin"}).status_code == 422
    assert admin.patch(url, json={"display_name": "x"}).status_code == 422
    detail = admin.get(url).json()
    assert detail["display_name"] == "New Name"
    assert "Some One -> New Name" in detail["history"][0]["detail"]


def test_an_admin_can_rename_themselves_but_not_change_their_role(admin, db_session):
    me = _uid(db_session, "boss@example.com")
    assert admin.patch(f"/api/admin/users/{me}", json={"display_name": "Big Boss"}).status_code == 200
    assert admin.patch(f"/api/admin/users/{me}", json={"role": "user"}).status_code == 409


def test_deleting_an_account(admin, make_client, db_session):
    c, uid = _someone(make_client, db_session)
    db_session.add(CatchPin(user_id=uid, latitude=1, longitude=1, title="Mine", status="published", visibility="public"))
    db_session.commit()
    assert admin.delete(f"/api/admin/users/{uid}").status_code == 204
    assert c.get("/api/auth/me").status_code == 401
    assert make_client().post("/api/auth/login", json={"email": "me@example.com", "password": PW}).status_code == 401
    db_session.expire_all()
    assert db_session.scalar(select(CatchPin)) is None
    entry = next(e for e in admin.get("/api/admin/audit").json()["items"] if e["action"] == "user.deleted_by_admin")
    assert "me@example.com" in entry["detail"]
    # The same address can sign up again.
    signup(make_client(), email="me@example.com", name="Some One")


def test_admins_arent_deleted_from_here(admin, make_client, db_session):
    me = _uid(db_session, "boss@example.com")
    assert admin.delete(f"/api/admin/users/{me}").status_code == 409
    _, uid = _someone(make_client, db_session)
    make_admin(db_session, "me@example.com")
    assert admin.delete(f"/api/admin/users/{uid}").status_code == 409
    assert admin.delete("/api/admin/users/999999").status_code == 404


@pytest.mark.parametrize(
    "method,suffix",
    [("GET", ""), ("DELETE", ""), ("POST", "/sign-out"), ("POST", "/confirm-email"), ("POST", "/reset-link")],
)
def test_ordinary_accounts_cant(make_client, db_session, method, suffix):
    c, uid = _someone(make_client, db_session)
    kw = {"json": {}} if suffix == "/reset-link" else {}
    assert c.request(method, f"/api/admin/users/{uid}{suffix}", **kw).status_code == 403
    assert make_client().request(method, f"/api/admin/users/{uid}{suffix}", **kw).status_code == 401
