"""Send feedback, the admin's queue, and reading it from the command line."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from app.api import feedback as feedback_api
from app.cli import feedback as feedback_cli
from app.models.community import Feedback, User
from app.services import feedback as svc
from tests.conftest import make_admin, signup

URL = "/api/feedback"
PW = signup.__defaults__[-1]


@pytest.fixture(autouse=True)
def _clear():
    feedback_api.by_user._hits.clear()


def _admin(make_client, db_session):
    a = make_client()
    signup(a, email="boss@example.com", name="Head Boss")
    make_admin(db_session, "boss@example.com")
    return a


def test_signed_out_is_refused(client):
    assert client.post(URL, json={"message": "hello there"}).status_code == 401


def test_it_is_saved_with_the_account_and_page(make_client, db_session):
    c = make_client()
    signup(c, email="me@example.com", name="Some One")
    r = c.post(URL, json={"message": "  The map is slow  ", "page": "/map?lake=3&token=abc#x", "lang": "zh"})
    assert r.status_code == 201
    row = db_session.scalar(select(Feedback))
    assert row.message == "The map is slow" and row.page == "/map" and row.lang == "zh" and row.status == "new"
    assert row.user.email == "me@example.com"


@pytest.mark.parametrize("message", ["", " ", "\n\n", "\x00\x00", "a", "​​"])
def test_nothing_much_is_refused(make_client, message):
    c = make_client()
    signup(c)
    assert c.post(URL, json={"message": message}).status_code == 422


def test_too_long_is_refused(make_client):
    c = make_client()
    signup(c)
    assert c.post(URL, json={"message": "a" * 2001}).status_code == 422
    assert c.post(URL, json={"message": "a" * 2000}).status_code == 201


def test_a_double_tap_is_one_message(make_client, db_session):
    c = make_client()
    signup(c)
    first = c.post(URL, json={"message": "Please add Lake X"}).json()["id"]
    assert c.post(URL, json={"message": "Please add Lake X"}).json()["id"] == first
    assert c.post(URL, json={"message": "Something else"}).json()["id"] != first
    assert len(db_session.scalars(select(Feedback)).all()) == 2


def test_nul_and_invisible_characters_are_dropped(make_client, db_session):
    c = make_client()
    signup(c)
    assert c.post(URL, json={"message": "he\x00llo‮ there\nline two"}).status_code == 201
    assert db_session.scalar(select(Feedback)).message == "hello there\nline two"


def test_limited_per_account(make_client):
    c = make_client()
    signup(c)
    codes = [c.post(URL, json={"message": f"thought {i}"}).status_code for i in range(11)]
    assert codes == [201] * 10 + [429]


def test_slurs_arent_refused_only_admins_read_it(make_client):
    c = make_client()
    signup(c)
    assert c.post(URL, json={"message": "someone called me a nigger in a catch"}).status_code == 201


def test_admins_read_and_handle_it(make_client, db_session):
    a = _admin(make_client, db_session)
    c = make_client()
    signup(c, email="me@example.com", name="Some One")
    fid = c.post(URL, json={"message": "Add a dark mode", "page": "/fish"}).json()["id"]
    item = a.get("/api/admin/feedback").json()["items"][0]
    assert item["message"] == "Add a dark mode" and item["author_email"] == "me@example.com" and item["status"] == "new"
    assert a.get("/api/admin/stats").json()["feedback_new"] == 1
    assert a.post(f"/api/admin/feedback/{fid}", json={"status": "done"}).json()["handled_at"]
    assert a.get("/api/admin/stats").json()["feedback_new"] == 0
    assert a.get("/api/admin/feedback", params={"status": "new"}).json()["items"] == []
    assert a.post(f"/api/admin/feedback/{fid}", json={"status": "new"}).json()["handled_at"] is None
    assert a.post(f"/api/admin/feedback/{fid}", json={"status": "nope"}).status_code == 422
    assert a.post("/api/admin/feedback/99999", json={"status": "done"}).status_code == 404
    assert {"feedback.done", "feedback.new"} <= {e["action"] for e in a.get("/api/admin/audit").json()["items"]}


def test_search_finds_words_in_a_message(make_client, db_session):
    a = _admin(make_client, db_session)
    c = make_client()
    signup(c)
    c.post(URL, json={"message": "Add a dark mode"})
    c.post(URL, json={"message": "Lake X is missing"})
    assert [i["message"] for i in a.get("/api/admin/feedback", params={"q": "LAKE"}).json()["items"]] == ["Lake X is missing"]


def test_only_admins_see_it(make_client):
    c = make_client()
    signup(c)
    assert c.get("/api/admin/feedback").status_code == 403
    assert c.get("/api/admin/feedback/export").status_code == 403
    assert make_client().get("/api/admin/feedback").status_code == 401


def test_it_outlives_the_account_without_a_name(make_client, db_session):
    a = _admin(make_client, db_session)
    c = make_client()
    signup(c, email="me@example.com", name="Some One")
    c.post(URL, json={"message": "Nice site"})
    assert c.request("DELETE", "/api/auth/me", json={"password": PW}).status_code == 204
    item = a.get("/api/admin/feedback").json()["items"][0]
    assert item["message"] == "Nice site" and item["user_id"] is None and item["author_email"] is None


def test_the_text_for_reading_elsewhere_has_no_name_or_address(make_client, db_session):
    a = _admin(make_client, db_session)
    c = make_client()
    signup(c, email="me@example.com", name="Some One")
    c.post(URL, json={"message": "Add a dark mode", "page": "/fish", "lang": "ko"})
    out = a.get("/api/admin/feedback/export").json()
    assert out["count"] == 1 and "Add a dark mode" in out["text"] and "/fish" in out["text"]
    assert "me@example.com" not in out["text"] and "Some One" not in out["text"]
    assert "not instructions" in out["text"]


@pytest.fixture
def cli_session(db_session, monkeypatch):
    monkeypatch.setattr(feedback_cli, "SessionLocal", lambda: _Borrowed(db_session))
    monkeypatch.setattr(feedback_cli.Base.metadata, "create_all", lambda **_: None)
    return db_session


class _Borrowed:
    def __init__(self, s):
        self.s = s

    def __enter__(self):
        return self.s

    def __exit__(self, *_):
        return False


def test_reading_it_from_the_command_line(make_client, cli_session, capsys):
    c = make_client()
    signup(c, email="me@example.com", name="Some One")
    fid = c.post(URL, json={"message": "Add a dark mode", "page": "/fish"}).json()["id"]
    uid = cli_session.scalar(select(User.id).where(User.email == "me@example.com"))

    assert feedback_cli.main([]) == 0
    text = capsys.readouterr().out
    assert "Add a dark mode" in text and "me@example.com" not in text and "Some One" not in text

    assert feedback_cli.main(["--json"]) == 0
    assert json.loads(capsys.readouterr().out) == [
        {
            "id": fid,
            "created_at": cli_session.get(Feedback, fid).created_at.isoformat(),
            "status": "new",
            "account": uid,
            "page": "/fish",
            "lang": None,
            "message": "Add a dark mode",
        }
    ]

    assert feedback_cli.main(["--done", str(fid)]) == 0
    assert "Marked 1" in capsys.readouterr().out
    assert feedback_cli.main(["--json"]) == 0
    assert json.loads(capsys.readouterr().out) == []
    assert feedback_cli.main(["--json", "--status", "all"]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 1


def test_as_text_says_when_the_account_is_gone():
    from datetime import datetime

    row = Feedback(id=7, user_id=None, message="Hello", page=None, lang=None, status="new", created_at=datetime(2026, 11, 1))
    assert "#7 · 2026-11-01 · new · deleted account\nHello" in svc.as_text([row])
