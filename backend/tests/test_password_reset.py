"""Forgot password: services/password_reset.py, api/auth.py, and the admin's link."""
from __future__ import annotations

import re
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.api import auth as auth_api
from app.db.types import utcnow
from app.models.community import PasswordResetToken, User
from app.services import mail, password_reset
from tests.conftest import make_admin, signup

PW = "correct horse battery staple"
NEW = "a brand new long passphrase"
REQUEST = "/api/auth/password-reset/request"
CONFIRM = "/api/auth/password-reset/confirm"
CHECK = "/api/auth/password-reset/check"


@pytest.fixture(autouse=True)
def _clear():
    mail.outbox.clear()
    for limiter in (auth_api.reset_mail_by_email, auth_api.reset_by_ip, auth_api.verify_by_ip):
        limiter._hits.clear()


def _token() -> str:
    body = mail.outbox[-1].get_content()
    return re.search(r"token=([\w-]+)", body).group(1)


def _asked(make_client, email="me@example.com"):
    c = make_client()
    signup(c, email=email)
    mail.outbox.clear()
    assert make_client().post(REQUEST, json={"email": email}).status_code == 202
    return c


def test_the_answer_is_the_same_for_any_address(make_client):
    c = make_client()
    signup(c, email="me@example.com")
    mail.outbox.clear()
    known = make_client().post(REQUEST, json={"email": "me@example.com"})
    unknown = make_client().post(REQUEST, json={"email": "nobody@example.com"})
    junk = make_client().post(REQUEST, json={"email": "not an address"})
    assert known.status_code == unknown.status_code == junk.status_code == 202
    assert known.content == unknown.content == junk.content == b""
    assert len(mail.outbox) == 1 and mail.outbox[0]["To"] == "me@example.com"


def test_any_case_or_spacing_finds_the_account(make_client):
    c = make_client()
    signup(c, email="me@example.com")
    mail.outbox.clear()
    make_client().post(REQUEST, json={"email": "  ME@Example.COM "})
    assert len(mail.outbox) == 1


def test_a_reset_works_signs_you_in_and_ends_other_sessions(make_client):
    old_device = _asked(make_client)
    assert old_device.get("/api/auth/me").status_code == 200
    token = _token()
    browser = make_client()
    r = browser.post(CONFIRM, json={"token": token, "new_password": NEW})
    assert r.status_code == 200 and r.json()["email"] == "me@example.com"
    assert browser.get("/api/auth/me").status_code == 200
    assert old_device.get("/api/auth/me").status_code == 401
    assert make_client().post("/api/auth/login", json={"email": "me@example.com", "password": PW}).status_code == 401
    assert make_client().post("/api/auth/login", json={"email": "me@example.com", "password": NEW}).status_code == 200


def test_a_link_works_once(make_client):
    _asked(make_client)
    token = _token()
    assert make_client().post(CONFIRM, json={"token": token, "new_password": NEW}).status_code == 200
    r = make_client().post(CONFIRM, json={"token": token, "new_password": NEW + " again"})
    assert r.status_code == 400 and "expired" in r.json()["detail"]
    assert make_client().post(CHECK, json={"token": token}).json() == {"valid": False, "email": None}


def test_a_new_link_replaces_the_old(make_client):
    _asked(make_client)
    first = _token()
    make_client().post(REQUEST, json={"email": "me@example.com"})
    second = _token()
    assert first != second
    assert make_client().post(CONFIRM, json={"token": first, "new_password": NEW}).status_code == 400
    assert make_client().post(CONFIRM, json={"token": second, "new_password": NEW}).status_code == 200


def test_an_expired_link_is_refused_and_gone(make_client, db_session):
    _asked(make_client)
    token = _token()
    row = db_session.scalar(select(PasswordResetToken))
    row.expires_at = utcnow() - timedelta(minutes=1)
    db_session.commit()
    assert make_client().post(CHECK, json={"token": token}).json()["valid"] is False
    assert make_client().post(CONFIRM, json={"token": token, "new_password": NEW}).status_code == 400
    assert db_session.scalar(select(PasswordResetToken)) is None


@pytest.mark.parametrize("token", ["", "x", "a" * 200, "a\x00b"])
def test_junk_links_are_refused(client, token):
    assert client.post(CONFIRM, json={"token": token, "new_password": NEW}).status_code in (400, 422)
    r = client.post(CHECK, json={"token": token})
    assert r.status_code == 422 or r.json()["valid"] is False


def test_a_weak_password_leaves_the_link_working(make_client):
    _asked(make_client)
    token = _token()
    for bad in ("1", "password", "12345678"):
        r = make_client().post(CONFIRM, json={"token": token, "new_password": bad})
        assert r.status_code == 422, bad
    assert make_client().post(CHECK, json={"token": token}).json()["valid"] is True
    assert make_client().post(CONFIRM, json={"token": token, "new_password": NEW}).status_code == 200


def test_only_the_tokens_digest_is_stored(make_client, db_session):
    _asked(make_client)
    assert db_session.scalar(select(PasswordResetToken)).token_hash != _token()


def test_checking_a_link_doesnt_use_it(make_client):
    _asked(make_client)
    token = _token()
    for _ in range(3):
        assert make_client().post(CHECK, json={"token": token}).json() == {"valid": True, "email": "me@example.com"}


def test_a_suspended_account_gets_no_mail_and_cant_use_a_link(make_client, db_session):
    _asked(make_client)
    token = _token()
    db_session.scalar(select(User).where(User.email == "me@example.com")).status = "suspended"
    db_session.commit()
    mail.outbox.clear()
    make_client().post(REQUEST, json={"email": "me@example.com"})
    assert len(mail.outbox) == 0
    assert make_client().post(CHECK, json={"token": token}).json()["valid"] is False
    assert make_client().post(CONFIRM, json={"token": token, "new_password": NEW}).status_code == 400


def test_a_reset_confirms_the_address(make_client, db_session):
    _asked(make_client)
    make_client().post(CONFIRM, json={"token": _token(), "new_password": NEW})
    assert db_session.scalar(select(User).where(User.email == "me@example.com")).email_verified_at is not None


def test_requests_are_limited_without_saying_so(make_client):
    c = make_client()
    signup(c, email="me@example.com")
    mail.outbox.clear()
    codes = [make_client().post(REQUEST, json={"email": "me@example.com"}).status_code for _ in range(5)]
    assert codes == [202] * 5
    assert len(mail.outbox) == 3


def test_too_many_requests_from_one_place_are_refused(client):
    codes = [client.post(REQUEST, json={"email": f"p{i}@example.com"}).status_code for i in range(12)]
    assert codes[:10] == [202] * 10 and codes[10:] == [429, 429]


def test_the_mail_is_in_the_askers_language(make_client):
    c = make_client()
    signup(c, email="me@example.com")
    mail.outbox.clear()
    a = make_client()
    a.cookies.set("fisheye.lang", "zh")
    a.post(REQUEST, json={"email": "me@example.com"})
    assert mail.outbox[-1]["Subject"] == "重置你的 FishEye 密码" and "1 小时" in mail.outbox[-1].get_content()


def test_a_failed_send_still_answers_the_same(make_client, monkeypatch):
    c = make_client()
    signup(c, email="me@example.com")

    def boom(*_):
        raise mail.MailError("down")

    monkeypatch.setattr(mail, "send", boom)
    assert make_client().post(REQUEST, json={"email": "me@example.com"}).status_code == 202


def test_providers_say_whether_mail_can_go_out(client, monkeypatch):
    assert client.get("/api/auth/providers").json()["email_ready"] is False
    monkeypatch.setattr(password_reset, "can_email", lambda: True)
    assert client.get("/api/auth/providers").json()["email_ready"] is True


def _admin_and_user(make_client, db_session):
    admin = make_client()
    signup(admin, email="boss@example.com", name="Head Boss")
    make_admin(db_session, "boss@example.com")
    someone = make_client()
    signup(someone, email="me@example.com", name="Some One")
    uid = db_session.scalar(select(User.id).where(User.email == "me@example.com"))
    return admin, someone, uid


def test_an_admin_can_make_a_link_to_hand_over(make_client, db_session):
    admin, someone, uid = _admin_and_user(make_client, db_session)
    mail.outbox.clear()
    r = admin.post(f"/api/admin/users/{uid}/reset-link", json={})
    assert r.status_code == 200 and r.json()["emailed"] is False and len(mail.outbox) == 0
    token = r.json()["link"].split("token=")[1]
    assert make_client().post(CONFIRM, json={"token": token, "new_password": NEW}).status_code == 200
    assert someone.get("/api/auth/me").status_code == 401
    audit = admin.get("/api/admin/audit").json()["items"]
    assert {"user.reset_link", "user.password_reset"} <= {e["action"] for e in audit}
    assert token not in str(audit)


def test_an_admins_link_lasts_a_day(make_client, db_session):
    admin, _, uid = _admin_and_user(make_client, db_session)
    admin.post(f"/api/admin/users/{uid}/reset-link", json={})
    row = db_session.scalar(select(PasswordResetToken).where(PasswordResetToken.user_id == uid))
    assert row.expires_at - utcnow() > timedelta(hours=23)


def test_an_admin_can_email_it_when_the_server_can(make_client, db_session, monkeypatch):
    admin, _, uid = _admin_and_user(make_client, db_session)
    mail.outbox.clear()
    assert admin.post(f"/api/admin/users/{uid}/reset-link", json={"email_it": True}).json()["emailed"] is False
    monkeypatch.setattr(password_reset, "can_email", lambda: True)
    assert admin.post(f"/api/admin/users/{uid}/reset-link", json={"email_it": True}).json()["emailed"] is True
    assert mail.outbox[-1]["To"] == "me@example.com" and "24 hour" in mail.outbox[-1].get_content()


def test_links_arent_made_for_admins_or_by_non_admins(make_client, db_session):
    admin, someone, uid = _admin_and_user(make_client, db_session)
    me = db_session.scalar(select(User.id).where(User.email == "boss@example.com"))
    assert admin.post(f"/api/admin/users/{me}/reset-link", json={}).status_code == 409
    assert someone.post(f"/api/admin/users/{uid}/reset-link", json={}).status_code == 403
    assert make_client().post(f"/api/admin/users/{uid}/reset-link", json={}).status_code == 401
