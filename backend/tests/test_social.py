"""Likes, comments, leaderboards and catch alerts (docs/adr/0054)."""
from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.db.types import utcnow
from app.models.community import CatchPin, PinComment, PinLike, SpeciesAlert, User
from app.services import alerts, mail
from tests.conftest import make_admin, signup


def share(c, **fields):
    data = {"latitude": 32.8065, "longitude": -95.5931, "title": "Dam bank", **fields}
    resp = c.post("/api/pins", data=data)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture()
def two(make_client, seeded_lake):
    """Someone who shared a catch, and someone else."""
    owner, other = make_client(), make_client()
    signup(owner, email="owner@example.com", name="Owner")
    signup(other, email="other@example.com", name="Other")
    return owner, other, share(owner)


# ----------------------------------------------------------------- likes


def test_a_like_counts_once_and_can_be_taken_back(two):
    owner, other, pin = two
    url = f"/api/pins/{pin['id']}/like"
    assert other.post(url).json() == {"liked": True, "like_count": 1}
    assert other.post(url).json() == {"liked": True, "like_count": 1}
    seen = other.get(f"/api/pins/{pin['id']}").json()
    assert seen["like_count"] == 1 and seen["liked_by_me"]
    assert owner.get(f"/api/pins/{pin['id']}").json()["liked_by_me"] is False
    assert other.delete(url).json() == {"liked": False, "like_count": 0}


def test_list_of_catches_says_how_many_likes_and_comments(two):
    _, other, pin = two
    other.post(f"/api/pins/{pin['id']}/like")
    other.post(f"/api/pins/{pin['id']}/comments", json={"body": "Nice one"})
    row = next(p for p in other.get("/api/pins", params={"state": "TX"}).json() if p["id"] == pin["id"])
    assert (row["like_count"], row["comment_count"], row["liked_by_me"]) == (1, 1, True)


def test_you_cant_like_your_own_catch(two):
    owner, _, pin = two
    assert owner.post(f"/api/pins/{pin['id']}/like").status_code == 422


def test_liking_needs_an_account(two, make_client):
    _, _, pin = two
    assert make_client().post(f"/api/pins/{pin['id']}/like").status_code == 401


def test_a_private_catch_cant_be_liked_or_commented_on(make_client, seeded_lake):
    owner = make_client()
    signup(owner)
    pin = share(owner, visibility="private")
    other = make_client()
    signup(other, email="b@example.com")
    assert other.post(f"/api/pins/{pin['id']}/like").status_code == 404
    assert other.post(f"/api/pins/{pin['id']}/comments", json={"body": "hi"}).status_code == 404


# -------------------------------------------------------------- comments


def test_comments_read_in_order_and_say_who_can_delete(two, make_client):
    owner, other, pin = two
    url = f"/api/pins/{pin['id']}/comments"
    first = other.post(url, json={"body": "  What bait?  "})
    assert first.status_code == 201 and first.json()["body"] == "What bait?"
    owner.post(url, json={"body": "A jig."})
    listed = make_client().get(url).json()
    assert [c["body"] for c in listed] == ["What bait?", "A jig."]
    assert [c["author"]["display_name"] for c in listed] == ["Other", "Owner"]
    assert not any(c["can_delete"] or c["can_report"] for c in listed)
    assert [c["can_delete"] for c in owner.get(url).json()] == [True, True]
    theirs = other.get(url).json()
    assert [c["can_delete"] for c in theirs] == [True, False] and [c["can_report"] for c in theirs] == [False, True]


def test_the_owner_of_the_catch_can_delete_a_comment_and_a_stranger_cant(two, make_client):
    owner, other, pin = two
    url = f"/api/pins/{pin['id']}/comments"
    cid = other.post(url, json={"body": "Spam"}).json()["id"]
    third = make_client()
    signup(third, email="c@example.com")
    assert third.delete(f"{url}/{cid}").status_code == 403
    assert owner.delete(f"{url}/{cid}").status_code == 204
    assert other.get(url).json() == []


@pytest.mark.parametrize("body", ["", "   "])
def test_an_empty_comment_is_refused(two, body):
    _, other, pin = two
    assert other.post(f"/api/pins/{pin['id']}/comments", json={"body": body}).status_code == 422


def test_a_comment_cant_be_too_long(two):
    _, other, pin = two
    assert other.post(f"/api/pins/{pin['id']}/comments", json={"body": "x" * 501}).status_code == 422


def test_a_slur_is_refused_in_a_comment(two):
    _, other, pin = two
    assert other.post(f"/api/pins/{pin['id']}/comments", json={"body": "you n1gg3r"}).status_code == 422


def test_enough_reports_hide_a_comment_and_a_moderator_can_bring_it_back(two, make_client, db_session):
    _, other, pin = two
    url = f"/api/pins/{pin['id']}/comments"
    cid = other.post(url, json={"body": "Rude"}).json()["id"]
    assert other.post(f"{url}/{cid}/reports", json={"reason": "other"}).status_code == 422  # their own
    for i in range(3):
        reporter = make_client()
        signup(reporter, email=f"r{i}@example.com")
        resp = reporter.post(f"{url}/{cid}/reports", json={"reason": "hateful"})
        assert resp.status_code == 201
        assert reporter.post(f"{url}/{cid}/reports", json={"reason": "hateful"}).status_code in (404, 409)
    assert resp.json()["hidden"] is True
    assert make_client().get(url).json() == []

    admin = make_client()
    signup(admin, email="admin@example.com")
    make_admin(db_session, "admin@example.com")
    queue = admin.get("/api/admin/comment-reports").json()
    assert [g["comment"]["id"] for g in queue] == [cid] and len(queue[0]["reports"]) == 3
    assert admin.post(f"/api/admin/comment-reports/{cid}/resolve", json={"action": "dismiss"}).status_code == 200
    assert [c["id"] for c in make_client().get(url).json()] == [cid]
    assert admin.get("/api/admin/comment-reports").json() == []


def test_a_moderator_can_remove_a_reported_comment(two, make_client, db_session):
    _, other, pin = two
    url = f"/api/pins/{pin['id']}/comments"
    cid = other.post(url, json={"body": "Rude"}).json()["id"]
    reporter = make_client()
    signup(reporter, email="r@example.com")
    reporter.post(f"{url}/{cid}/reports", json={"reason": "spam"})
    admin = make_client()
    signup(admin, email="admin@example.com")
    make_admin(db_session, "admin@example.com")
    assert admin.post(f"/api/admin/comment-reports/{cid}/resolve", json={"action": "remove"}).status_code == 200
    assert db_session.get(PinComment, cid) is None


def test_deleting_an_account_takes_its_likes_comments_and_alerts_with_it(two, db_session):
    _, other, pin = two
    other.post(f"/api/pins/{pin['id']}/like")
    other.post(f"/api/pins/{pin['id']}/comments", json={"body": "Hi"})
    other.post("/api/alerts", json={"species_slug": "bluegill", "latitude": 32.8, "longitude": -95.6, "place": "Home", "radius_miles": 30})
    assert other.request("DELETE", "/api/auth/me", json={"password": "tight-lines-42"}).status_code == 204
    db_session.expire_all()
    assert db_session.scalars(select(PinLike)).all() == []
    assert db_session.scalars(select(PinComment)).all() == []
    assert db_session.scalars(select(SpeciesAlert)).all() == []


# ---------------------------------------------------------- leaderboards


def _confirm(db, pin_id):
    db.get(CatchPin, pin_id).species_check = "confirmed"
    db.commit()


def test_catches_counts_only_what_the_photo_check_backed(two, db_session):
    owner, other, pin = two
    share(other)
    _confirm(db_session, pin["id"])
    board = other.get("/api/leaderboard", params={"metric": "catches", "period": "all"}).json()
    assert [(e["display_name"], e["value"], e["is_me"]) for e in board["entries"]] == [("Owner", 1, False)]
    assert board["me"] is None


def test_shares_ranks_by_public_catches_and_ties_share_a_place(two):
    owner, other, _ = two
    share(owner, title="Second one")
    share(owner, visibility="private", title="Private one")
    share(other)
    board = other.get("/api/leaderboard", params={"metric": "shares", "period": "all"}).json()
    assert [(e["rank"], e["display_name"], e["value"]) for e in board["entries"]] == [(1, "Owner", 2), (2, "Other", 1)]
    assert board["me"]["rank"] == 2 and board["me"]["is_me"]

    share(other, title="Now level")
    board = other.get("/api/leaderboard", params={"metric": "shares", "period": "all"}).json()
    assert [e["rank"] for e in board["entries"]] == [1, 1]


def test_active_counts_days_not_catches(two):
    owner, other, _ = two
    share(owner, caught_on="2026-09-01", title="One")
    share(owner, caught_on="2026-09-01", title="Two")
    share(other, caught_on="2026-09-01", title="Three")
    share(other, caught_on="2026-09-02", title="Four")
    rows = owner.get("/api/leaderboard", params={"metric": "active", "period": "all"}).json()["entries"]
    assert {e["display_name"]: e["value"] for e in rows} == {"Owner": 2, "Other": 2}


def test_likes_counts_likes_received(two):
    owner, other, pin = two
    other.post(f"/api/pins/{pin['id']}/like")
    rows = owner.get("/api/leaderboard", params={"metric": "likes", "period": "all"}).json()["entries"]
    assert [(e["display_name"], e["value"]) for e in rows] == [("Owner", 1)]


def test_a_board_is_for_a_place(two):
    owner, *_ = two
    assert owner.get("/api/leaderboard", params={"metric": "shares", "period": "all", "state": "GA"}).json()["entries"] == []


def test_the_month_leaves_out_what_is_older(two, db_session):
    owner, _, pin = two
    db_session.get(CatchPin, pin["id"]).created_at = utcnow() - timedelta(days=40)
    db_session.commit()
    assert owner.get("/api/leaderboard", params={"metric": "shares", "period": "30d"}).json()["entries"] == []
    assert len(owner.get("/api/leaderboard", params={"metric": "shares", "period": "all"}).json()["entries"]) == 1


def test_someone_can_leave_the_leaderboards(two):
    owner, *_ = two
    assert owner.patch("/api/auth/me", json={"hide_from_rankings": True}).json()["hide_from_rankings"] is True
    assert owner.get("/api/leaderboard", params={"metric": "shares", "period": "all"}).json()["entries"] == []
    # Their name stays: this only leaves the rankings.
    assert owner.get("/api/auth/me").json()["display_name"] == "Owner"


def test_an_unknown_board_is_refused(two):
    owner, *_ = two
    assert owner.get("/api/leaderboard", params={"metric": "nope"}).status_code == 422
    assert owner.get("/api/leaderboard", params={"period": "nope"}).status_code == 422


# --------------------------------------------------------------- anglers


def test_an_anglers_page_shows_only_what_they_share(two, db_session):
    owner, other, pin = two
    share(owner, visibility="private", title="Secret spot")
    other.post(f"/api/pins/{pin['id']}/like")
    _confirm(db_session, pin["id"])
    me = owner.get("/api/auth/me").json()
    page = other.get(f"/api/anglers/{me['id']}").json()
    assert (page["display_name"], page["catches"], page["confirmed"], page["likes"]) == ("Owner", 1, 1, 1)
    assert "email" not in page
    listed = owner.get("/api/pins", params={"author": me["id"]}).json()
    assert [p["id"] for p in listed] == [pin["id"]]


def test_someone_with_nothing_public_has_no_page(make_client, seeded_lake):
    c = make_client()
    signup(c)
    assert c.get(f"/api/anglers/{c.get('/api/auth/me').json()['id']}").status_code == 404


# ---------------------------------------------------------------- alerts


def alert(c, **fields):
    data = {"species_slug": "bluegill", "latitude": 32.81, "longitude": -95.6, "place": "Lake Fork", "radius_miles": 30, "lang": "en", **fields}
    return c.post("/api/alerts", json=data)


@pytest.fixture()
def watcher(make_client, seeded_lake, db_session):
    c = make_client()
    signup(c, email="watcher@example.com", name="Watcher")
    user = db_session.scalar(select(User).where(User.email == "watcher@example.com"))
    user.email_verified_at = utcnow()
    db_session.commit()
    assert alert(c).status_code == 201
    return c


def caught(c, db, **fields):
    pin = db.get(CatchPin, share(c, species_slug="bluegill", **fields)["id"])
    pin.species_check = "confirmed"
    db.commit()
    return pin


@pytest.fixture()
def angler_client(make_client):
    c = make_client()
    signup(c, email="angler@example.com", name="Angler")
    return c


def test_a_confirmed_catch_inside_the_radius_is_emailed(watcher, angler_client, db_session):
    pin = caught(angler_client, db_session)
    notices = alerts.notices_for(db_session, pin)
    assert [n.to for n in notices] == ["watcher@example.com"]
    assert "Bluegill" in notices[0].subject and "Lake Fork" in notices[0].subject
    assert f"/community/{pin.id}" in notices[0].text and "/unsubscribe?token=" in notices[0].text
    # Nothing that says who caught it, or where exactly.
    assert "Angler" not in notices[0].text and "32.8065" not in notices[0].text


def test_written_in_the_language_of_the_alert(make_client, seeded_lake, angler_client, db_session):
    c = make_client()
    signup(c, email="zh@example.com")
    db_session.scalar(select(User).where(User.email == "zh@example.com")).email_verified_at = utcnow()
    db_session.commit()
    alert(c, lang="zh")
    notices = alerts.notices_for(db_session, caught(angler_client, db_session))
    assert "附近有人钓到了" in notices[0].subject and "英里" in notices[0].text


def test_an_alert_set_in_traditional_chinese_writes_in_traditional(make_client, seeded_lake, angler_client, db_session):
    """The site sends 繁體 requests on as zh (api/zh_hant.py); the alert
    still remembers zht, and its emails come in Traditional."""
    c = make_client()
    signup(c, email="zht@example.com")
    db_session.scalar(select(User).where(User.email == "zht@example.com")).email_verified_at = utcnow()
    db_session.commit()
    made = alert(c, lang="zht")
    assert made.status_code == 201, made.text
    assert db_session.scalar(select(SpeciesAlert).where(SpeciesAlert.id == made.json()["id"])).lang == "zht"
    notices = alerts.notices_for(db_session, caught(angler_client, db_session))
    mine = next(n for n in notices if n.to == "zht@example.com")
    assert "附近有人釣到了" in mine.subject and "英里" in mine.text, mine
    assert "钓" not in mine.subject + mine.text


def test_outside_the_radius_nothing_is_sent(make_client, seeded_lake, angler_client, db_session):
    c = make_client()
    signup(c, email="far@example.com")
    db_session.scalar(select(User).where(User.email == "far@example.com")).email_verified_at = utcnow()
    db_session.commit()
    alert(c, latitude=30.27, longitude=-97.74, radius_miles=30)
    assert alerts.notices_for(db_session, caught(angler_client, db_session)) == []


def test_only_that_fish(watcher, angler_client, db_session):
    pin = db_session.get(CatchPin, share(angler_client, species_slug="largemouth-bass")["id"])
    pin.species_check = "confirmed"
    db_session.commit()
    assert alerts.notices_for(db_session, pin) == []


def test_a_catch_the_photo_check_didnt_back_is_not_a_confirmed_catch(watcher, angler_client, db_session):
    pin = db_session.get(CatchPin, share(angler_client, species_slug="bluegill")["id"])
    assert pin.species_check is None
    assert alerts.notices_for(db_session, pin) == []


def test_a_private_catch_tells_nobody(watcher, angler_client, db_session):
    assert alerts.notices_for(db_session, caught(angler_client, db_session, visibility="private")) == []


def test_your_own_catch_doesnt_email_you(watcher, db_session):
    assert alerts.notices_for(db_session, caught(watcher, db_session)) == []


def test_at_most_one_email_per_alert_in_twelve_hours(watcher, angler_client, db_session):
    first = caught(angler_client, db_session)
    assert len(alerts.notices_for(db_session, first)) == 1
    db_session.commit()
    second = caught(angler_client, db_session, title="Another one")
    assert alerts.notices_for(db_session, second) == []
    row = db_session.scalar(select(SpeciesAlert))
    row.last_sent_at = utcnow() - timedelta(hours=13)
    db_session.commit()
    assert len(alerts.notices_for(db_session, second)) == 1


def test_an_unconfirmed_address_is_not_emailed(make_client, seeded_lake, angler_client, db_session):
    c = make_client()
    signup(c, email="unconfirmed@example.com")
    alert(c)
    assert c.get("/api/alerts").json()["email_confirmed"] is False
    assert alerts.notices_for(db_session, caught(angler_client, db_session)) == []


def test_distance_is_to_the_public_point_not_the_spot(watcher, angler_client, db_session):
    pin = caught(angler_client, db_session)
    pin.public_latitude, pin.public_longitude = 45.0, -100.0
    db_session.commit()
    assert alerts.notices_for(db_session, pin) == []


def test_posting_a_catch_sends_the_email_after_the_response(watcher, angler_client, db_session, monkeypatch):
    def confirmed(pin, check, photo):
        pin.species_check = "confirmed"

    monkeypatch.setattr("app.services.pins._record_check", confirmed)
    mail.outbox.clear()
    share(angler_client, species_slug="bluegill")
    assert [m["To"] for m in mail.outbox] == ["watcher@example.com"]


def test_alert_limits(make_client, seeded_lake):
    c = make_client()
    signup(c)
    assert alert(c, species_slug="not-a-fish").status_code == 422
    assert alert(c, radius_miles=0).status_code == 422
    assert alert(c, radius_miles=501).status_code == 422
    assert alert(c, place="   ").status_code == 422
    for _ in range(10):
        assert alert(c).status_code == 201
    assert alert(c).status_code == 409


def test_where_an_alert_is_kept_to_about_a_kilometre(make_client, seeded_lake, db_session):
    c = make_client()
    signup(c)
    alert(c, latitude=32.80651, longitude=-95.59312)
    row = db_session.scalar(select(SpeciesAlert))
    assert (row.latitude, row.longitude) == (32.81, -95.59)


def test_only_your_own_alerts(two):
    owner, other, _ = two
    aid = alert(owner).json()["id"]
    assert other.get("/api/alerts").json()["alerts"] == []
    assert other.delete(f"/api/alerts/{aid}").status_code == 404
    assert owner.delete(f"/api/alerts/{aid}").status_code == 204


def test_alerts_need_an_account(make_client):
    assert make_client().get("/api/alerts").status_code == 401


def test_the_link_in_the_email_unsubscribes_without_signing_in(two, make_client, db_session):
    owner, *_ = two
    alert(owner)
    token = db_session.scalar(select(SpeciesAlert)).token
    stranger = make_client()
    assert stranger.post("/api/alerts/unsubscribe", json={"token": "wrong"}).status_code == 404
    assert stranger.post("/api/alerts/unsubscribe", json={"token": token}).json()["species_label"] == "Bluegill"
    assert owner.get("/api/alerts").json()["alerts"] == []
    assert stranger.post("/api/alerts/unsubscribe", json={"token": token}).status_code == 404
