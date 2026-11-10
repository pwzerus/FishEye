"""The visit counter: counts per page and day, and nothing about who."""
from __future__ import annotations

from sqlalchemy import inspect, select

from app.models.visits import PageVisit
from app.services import visits as svc
from tests.conftest import make_admin, signup

URL = "/api/visits"


def test_a_visit_is_a_count_and_nothing_else(client, db_session):
    for _ in range(3):
        assert client.post(URL, json={"path": "/map?lake=12", "referrer": "https://www.reddit.com/r/bassfishing/x"}).status_code == 204
    rows = db_session.scalars(select(PageVisit)).all()
    assert [(r.path, r.source, r.count) for r in rows] == [("/map", "reddit.com", 3)]
    # The table has no column that could tell one visitor from another.
    columns = {c["name"] for c in inspect(db_session.get_bind()).get_columns("page_visits")}
    assert columns == {"id", "day", "path", "source", "count"}


def test_no_cookie_is_set(client):
    r = client.post(URL, json={"path": "/"})
    assert "set-cookie" not in r.headers


def test_a_tagged_link_beats_the_referrer(client, db_session):
    client.post(URL, json={"path": "/", "referrer": "https://www.google.com/", "ref": " Reddit "})
    assert db_session.scalar(select(PageVisit)).source == "ref:reddit"


def test_pages_are_counted_by_kind_where_the_rest_is_someones():
    assert svc.clean_path("/fish/largemouth-bass") == "/fish/largemouth-bass"
    assert svc.clean_path("/community/123") == "/community/:id"
    assert svc.clean_path("/sources/") == "/sources"
    assert svc.clean_path("/") == "/"
    for skipped in ("/admin", "/admin/x", "/account", "/reset-password", "/api/visits", "https://x.com/", "", None, "/<script>"):
        assert svc.clean_path(skipped) is None


def test_the_site_itself_is_not_a_source():
    assert svc.clean_source("https://fisheye.app/map", None, "fisheye.app") == ""
    assert svc.clean_source("http://localhost:3000/", None, "localhost") == ""
    assert svc.clean_source("not a url", None, None) == ""
    assert svc.clean_source(None, "x" * 100, None) == "ref:" + "x" * 40


def test_one_client_cant_inflate_the_counts(client, db_session):
    codes = {client.post(URL, json={"path": "/"}).status_code for _ in range(61)}
    assert codes == {204, 429}


def test_admins_read_the_numbers(make_client, db_session):
    visitor = make_client()
    visitor.post(URL, json={"path": "/fish/bluegill", "ref": "xhs"})
    visitor.post(URL, json={"path": "/fish/bluegill"})
    a = make_client()
    signup(a, email="boss@example.com")
    make_admin(db_session, "boss@example.com")
    body = a.get(f"{URL}/summary?days=7").json()
    assert body["total"] == 2
    assert body["by_page"] == [{"key": "/fish/bluegill", "count": 2}]
    assert {s["key"] for s in body["by_source"]} == {"ref:xhs", ""}
    assert "2 page views" in body["text"]


def test_only_admins_read_them(make_client):
    c = make_client()
    assert c.get(f"{URL}/summary").status_code == 401
    signup(c)
    assert c.get(f"{URL}/summary").status_code == 403
