"""Confirming an account's email address (services/email_verification.py):
off by default; when on, sharing and reporting wait for the emailed link."""
from __future__ import annotations

import re
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.db.types import utcnow
from app.models.community import EmailToken, User
from app.services import mail
from app.services.auth import GoogleProfile, google_sign_in
from tests.conftest import make_admin, signup


def create_pin(c):
    return c.post("/api/pins", data={"latitude": 32.8, "longitude": -95.6, "title": "Dam bank"})


def last_link() -> str:
    body = mail.outbox[-1].get_content()
    return re.search(r"/verify-email\?token=(\S+)", body).group(1)


@pytest.fixture()
def verification_on(monkeypatch):
    monkeypatch.setattr(get_settings(), "email_verification", "on")
    monkeypatch.setattr(get_settings(), "mail_backend", "console")
    mail.outbox.clear()


def test_off_by_default_nothing_is_sent_and_nothing_waits(make_client):
    mail.outbox.clear()
    c = make_client()
    me = signup(c)
    assert (me["email_verified"], me["verification_required"]) == (False, False)
    assert len(mail.outbox) == 0
    assert create_pin(c).status_code == 201


def test_when_on_a_new_account_confirms_by_the_emailed_link(make_client, verification_on):
    c = make_client()
    me = signup(c)
    assert me["verification_required"] is True
    msg = mail.outbox[-1]
    assert msg["To"] == "angler@example.com" and msg["Subject"] == "Confirm your email for FishEye"

    refused = create_pin(c)
    assert refused.status_code == 403 and "Confirm your email" in refused.json()["detail"]

    # The link works signed out (another device), and only once.
    token = last_link()
    other_device = make_client()
    assert other_device.post("/api/auth/verify-email", json={"token": token}).json() == {
        "verified": True, "email": "angler@example.com",
    }
    assert other_device.post("/api/auth/verify-email", json={"token": token}).status_code == 400
    me = c.get("/api/auth/me").json()
    assert (me["email_verified"], me["verification_required"]) == (True, False)
    assert create_pin(c).status_code == 201


def test_a_new_link_replaces_the_old_and_expired_links_fail(make_client, db_session, verification_on):
    c = make_client()
    signup(c)
    first = last_link()
    assert c.post("/api/auth/verify-email/send").status_code == 200
    second = last_link()
    assert first != second
    assert c.post("/api/auth/verify-email", json={"token": first}).status_code == 400

    row = db_session.scalar(select(EmailToken))
    row.expires_at = utcnow() - timedelta(minutes=1)
    db_session.commit()
    expired = c.post("/api/auth/verify-email", json={"token": second})
    assert expired.status_code == 400 and "expired" in expired.json()["detail"]
    assert db_session.scalar(select(EmailToken)) is None


def test_reporting_waits_too_and_admins_never_wait(make_client, db_session, verification_on):
    admin = make_client()
    signup(admin, email="admin@example.com", name="Admin")
    make_admin(db_session, "admin@example.com")
    pin = create_pin(admin)
    assert pin.status_code == 201

    c = make_client()
    signup(c)
    report = c.post(f"/api/pins/{pin.json()['id']}/reports", json={"reason": "spam"})
    assert report.status_code == 403


def test_resending_is_limited(make_client, verification_on):
    c = make_client()
    signup(c)
    codes = [c.post("/api/auth/verify-email/send").status_code for _ in range(6)]
    assert codes[:5] == [200] * 5 and codes[5] == 429


def test_a_failed_send_still_creates_the_account(make_client, monkeypatch, verification_on):
    monkeypatch.setattr(get_settings(), "mail_backend", "smtp")
    monkeypatch.setattr(get_settings(), "smtp_host", None)  # MailError
    c = make_client()
    assert signup(c)["verification_required"] is True
    assert c.post("/api/auth/verify-email/send").status_code == 502


def test_google_confirms_the_address_it_signs_in(db_session, verification_on):
    user = google_sign_in(db_session, GoogleProfile(sub="g-1", email="new@example.com", name="New"), None)
    assert user.email_verified_at is not None

    local = User(email="pw@example.com", display_name="Pw", password_hash="x")
    db_session.add(local)
    db_session.flush()
    google_sign_in(db_session, GoogleProfile(sub="g-2", email="other@example.com", name="Pw"), local)
    assert local.email_verified_at is None  # a different address proves nothing about this one
    google_sign_in(db_session, GoogleProfile(sub="g-2", email="pw@example.com", name="Pw"), local)
    assert local.email_verified_at is not None
