"""Questions Ask couldn't answer: recorded without who asked, counted, kept 90 days."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from app.models.community import AskMiss
from app.services import ask_misses
from app.services.ai_quota import today
from tests.conftest import make_admin, signup


def test_scrub_takes_out_addresses_numbers_and_links():
    text = ask_misses.scrub("Call me at (512) 555-0187 or bob@example.com, see https://x.example/a  about a 10 lb cat in 2026")
    assert text == "Call me at [number] or [email], see [link] about a 10 lb cat in 2026"
    assert len(ask_misses.scrub("a" * 1000)) == ask_misses.MAX_CHARS
    assert ask_misses.scrub("bass​\x00 bait") == "bass bait"


def test_a_repeat_is_counted_and_old_rows_go(db_session):
    old = today() - timedelta(days=ask_misses.RETENTION_DAYS + 1)
    ask_misses.record(db_session, "Old question", "no_match", "en", day=old)
    for q in ("Where are the grayling?", "where are the  GRAYLING?"):
        ask_misses.record(db_session, q, "unguided_fish", "en", "MT")
    ask_misses.record(db_session, "Where are the grayling?", "no_match", "en")
    ask_misses.record(db_session, "fine question", "ok", "en")  # not a miss
    rows = db_session.scalars(select(AskMiss).order_by(AskMiss.id)).all()
    assert [(r.outcome, r.count, r.state) for r in rows] == [("unguided_fish", 2, "MT"), ("no_match", 1, None)]
    top = ask_misses.top(db_session)
    assert top[0].question == "Where are the grayling?" and top[0].count == 2 and top[0].days == 1


def test_ask_records_misses_and_admins_read_them(make_client, client, db_session):
    assert client.post("/api/ask", json={"question": "How do I bake sourdough bread?"}).status_code == 200
    assert client.post("/api/ask", json={"question": "How do I bake sourdough bread?"}).status_code == 200
    assert client.post("/api/ask", json={"question": "What bait for channel catfish?"}).status_code == 200
    rows = db_session.scalars(select(AskMiss)).all()
    assert [(r.outcome, r.count) for r in rows] == [("off_topic", 2)]

    admin = make_client()
    signup(admin, email="admin@example.com", name="Admin")
    make_admin(db_session, "admin@example.com")
    listed = admin.get("/api/admin/ask-misses").json()
    assert listed == [
        {
            "question": "How do I bake sourdough bread?",
            "outcome": "off_topic",
            "lang": "en",
            "state": None,
            "species_slug": None,
            "count": 2,
            "days": 1,
            "last_day": today().isoformat(),
        }
    ]
    assert admin.get("/api/admin/ask-misses?outcome=no_match").json() == []
    assert make_client().get("/api/admin/ask-misses").status_code == 401
