"""AI summaries of guide answers: account-only, a few per day, and only for
questions the guides cover (app/api/ask.py, services/ai_quota.py, ADR 0023).

The model here is the mock provider (no key in tests), which writes a valid,
grounded answer unless told to fail.
"""
from datetime import date

import pytest

from app.services import ai_quota, llm
from app.services.rag import ask as rag
from tests.conftest import make_admin, signup

QUESTION = {"question": "what bait for crappie"}


@pytest.fixture(autouse=True)
def _fresh_answer_cache():
    rag.reset_cache()
    yield
    rag.reset_cache()


def summary(c, question: str = QUESTION["question"]):
    return c.post("/api/ask/summary", json={"question": question})


def signed_in(make_client, email: str = "angler@example.com"):
    c = make_client()
    signup(c, email=email)
    return c


def test_searching_needs_no_account_and_says_how_many_summaries_are_left(make_client):
    c = make_client()
    assert c.post("/api/ask", json=QUESTION).json()["ai"]["signed_in"] is False

    signup(c)
    body = c.post("/api/ask", json=QUESTION).json()
    assert body["answer_source"] == "passages"
    assert body["ai"] == {"signed_in": True, "limit": 3, "remaining": 3}
    assert c.get("/api/ask/allowance").json() == {"signed_in": True, "limit": 3, "remaining": 3}


def test_a_summary_needs_an_account(make_client):
    resp = summary(make_client())
    assert resp.status_code == 401


def test_a_summary_is_written_by_the_model_and_uses_one_of_the_allowance(make_client):
    c = signed_in(make_client)
    resp = summary(c)
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer_source"] == "llm"
    assert body["citations"]
    assert body["ai"]["remaining"] == 2


def test_after_the_daily_allowance_summaries_are_refused_but_search_still_works(make_client):
    c = signed_in(make_client)
    questions = ["what bait for crappie", "what lure for largemouth", "what do bluegill eat"]
    for q in questions:
        assert summary(c, q).status_code == 200

    refused = summary(c, "where do white bass go in spring")
    assert refused.status_code == 429
    assert "today's 3 AI summaries" in refused.json()["detail"]
    assert "still free" in refused.json()["detail"]

    search = c.post("/api/ask", json={"question": "where do white bass go in spring"})
    assert search.status_code == 200 and search.json()["citations"]
    assert search.json()["ai"]["remaining"] == 0


@pytest.mark.parametrize(
    "question",
    ["what is the capital of france", "how to tie a tie", "where is the nearest hospital"],
)
def test_a_question_the_guides_dont_cover_never_reaches_the_model_or_the_allowance(
    make_client, question, monkeypatch
):
    c = signed_in(make_client)
    calls = []
    monkeypatch.setattr(rag, "get_provider", lambda: calls.append(1))

    resp = summary(c, question)
    assert resp.status_code == 422
    assert "Nothing was used" in resp.json()["detail"]
    assert calls == []
    assert c.get("/api/ask/allowance").json()["remaining"] == 3


def test_a_summary_the_model_couldnt_write_is_given_back(make_client, monkeypatch):
    c = signed_in(make_client)
    monkeypatch.setenv("LLM_MOCK_FAILURE_MODE", "unavailable")
    llm.reset_provider_cache()
    try:
        body = summary(c).json()
    finally:
        monkeypatch.delenv("LLM_MOCK_FAILURE_MODE")
        llm.reset_provider_cache()
    assert body["answer_source"] == "fallback"
    assert body["trace"]["outcome"] == "provider_unavailable"
    assert body["ai"]["remaining"] == 3


def test_an_answer_from_the_cache_costs_nothing_and_is_not_counted(make_client):
    c = signed_in(make_client)
    assert summary(c).json()["ai"]["remaining"] == 2
    again = summary(c).json()
    assert again["trace"]["cache_hit"] is True
    assert again["ai"]["remaining"] == 2


def test_each_account_has_its_own_allowance(make_client):
    first, second = signed_in(make_client, "a@example.com"), signed_in(make_client, "b@example.com")
    for q in ["what bait for crappie", "what lure for largemouth", "what do bluegill eat"]:
        summary(first, q)
    assert summary(first, "what do sand bass eat").status_code == 429
    assert summary(second, "what do sand bass eat").status_code == 200


def test_the_allowance_starts_again_the_next_day(make_client, monkeypatch):
    c = signed_in(make_client)
    monkeypatch.setattr(ai_quota, "today", lambda: date(2026, 10, 18))
    for q in ["what bait for crappie", "what lure for largemouth", "what do bluegill eat"]:
        summary(c, q)
    assert summary(c, "what do sand bass eat").status_code == 429

    monkeypatch.setattr(ai_quota, "today", lambda: date(2026, 10, 19))
    assert summary(c, "what do sand bass eat").status_code == 200


def test_admins_are_not_limited(make_client, db_session):
    c = signed_in(make_client, "owner@example.com")
    make_admin(db_session, "owner@example.com")
    questions = [
        "what bait for crappie",
        "what lure for largemouth",
        "what do bluegill eat",
        "what do sand bass eat",
        "what rod for stripers",
    ]
    for q in questions:
        resp = summary(c, q)
        assert resp.status_code == 200
        assert resp.json()["ai"] == {"signed_in": True, "limit": None, "remaining": None}


def test_the_last_summary_cannot_be_taken_twice(db_session, make_client):
    """reserve() is one conditional UPDATE: at the limit it takes nothing."""
    from sqlalchemy import select

    from app.models.community import User

    signed_in(make_client)
    user = db_session.scalar(select(User))
    day = date(2026, 10, 18)
    assert [ai_quota.reserve(db_session, user, day) for _ in range(5)] == [True] * 3 + [False] * 2
    assert ai_quota.allowance(db_session, user, day).used == 3


def test_a_summary_from_another_site_is_refused(make_client):
    c = signed_in(make_client)
    resp = c.post("/api/ask/summary", json=QUESTION, headers={"Origin": "https://evil.example"})
    assert resp.status_code == 403
