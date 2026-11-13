"""AI answers on Ask: account-only, one a day on a free account, no limit on
FishEye Plus, and only for questions the guides cover (app/api/ask.py,
services/ai_quota.py, ADR 0023).

The model here is the mock provider (no key in tests), which writes a valid,
grounded answer unless told to fail.
"""
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.db.types import utcnow
from app.models.community import User
from app.services import ai_quota, llm
from app.services.rag import ask as rag
from tests.conftest import make_admin, signup

QUESTION = {"question": "what bait for crappie"}
FREE = {"signed_in": True, "limit": 1, "remaining": 1, "enabled": False, "plus": False}
UNLIMITED = {"signed_in": True, "limit": None, "remaining": None, "enabled": False}


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


def make_plus(db_session, email: str, days: int = 30) -> None:
    user = db_session.scalar(select(User).where(User.email == email))
    user.plus_until = utcnow() + timedelta(days=days)
    db_session.commit()


def test_searching_needs_no_account_and_says_how_many_summaries_are_left(make_client):
    c = make_client()
    assert c.post("/api/ask", json=QUESTION).json()["ai"]["signed_in"] is False

    signup(c)
    body = c.post("/api/ask", json=QUESTION).json()
    assert body["answer_source"] == "passages"
    assert body["ai"] == FREE
    assert c.get("/api/ask/allowance").json() == body["ai"]


def test_a_summary_needs_an_account(make_client):
    resp = summary(make_client())
    assert resp.status_code == 401


def test_a_summary_is_written_by_the_model_and_uses_the_days_one(make_client):
    c = signed_in(make_client)
    resp = summary(c)
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer_source"] == "llm"
    assert body["citations"]
    assert body["ai"]["remaining"] == 0


def test_after_the_days_one_summaries_are_refused_but_search_still_works(make_client):
    c = signed_in(make_client)
    assert summary(c, "what bait for crappie").status_code == 200

    refused = summary(c, "where do white bass go in spring")
    assert refused.status_code == 429
    assert "today's free AI answer" in refused.json()["detail"]
    assert "still free" in refused.json()["detail"]

    search = c.post("/api/ask", json={"question": "where do white bass go in spring"})
    assert search.status_code == 200 and search.json()["citations"]
    assert search.json()["ai"]["remaining"] == 0


@pytest.mark.parametrize(
    "question",
    ["what is the capital of france", "how to tie a tie", "where is the nearest hospital"],
)
def test_a_question_that_isnt_about_fishing_never_reaches_the_model_or_the_allowance(
    make_client, question, monkeypatch
):
    c = signed_in(make_client)
    calls = []
    monkeypatch.setattr(rag, "get_provider", lambda: calls.append(1))

    assert c.post("/api/ask", json={"question": question}).json()["ai_can_answer"] is False
    resp = summary(c, question)
    assert resp.status_code == 422
    assert "Nothing was used" in resp.json()["detail"]
    assert calls == []
    assert c.get("/api/ask/allowance").json()["remaining"] == 1


# The product owner, 2026-11-12: where the guides stop, the AI answers from
# its own fishing knowledge.
def test_a_fishing_question_the_guides_dont_cover_gets_an_ai_answer(make_client):
    c = signed_in(make_client)
    search = c.post("/api/ask", json={"question": "how do I smoke a carp"}).json()
    assert search["answer_source"] == "no_match"
    assert search["ai_can_answer"] is True

    body = summary(c, "how do I smoke a carp").json()
    assert body["answer_source"] == "llm"
    assert body["citations"] == []
    assert body["ai"]["remaining"] == 0


def test_the_guides_passages_can_be_followed_by_an_ai_answer(make_client):
    assert make_client().post("/api/ask", json=QUESTION).json()["ai_can_answer"] is True


def test_an_answer_the_model_calls_off_topic_is_given_back(make_client, monkeypatch):
    c = signed_in(make_client)
    monkeypatch.setattr(rag, "get_provider", lambda: _OffTopic())
    body = summary(c, "how do I smoke a carp").json()
    assert body["answer_source"] == "no_match"
    assert body["trace"]["outcome"] == "off_topic"
    assert body["ai"]["remaining"] == 1


class _OffTopic(llm.LLMProvider):
    name = "scripted"

    def complete(self, system_prompt: str, user_prompt: str) -> llm.LLMResponse:
        return llm.LLMResponse(
            text='{"off_topic": true}', provider=self.name, model="scripted", prompt_tokens=1,
            completion_tokens=1, estimated_cost_usd=0.0, latency_ms=0.0,
        )


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
    assert body["ai"]["remaining"] == 1


def test_an_answer_from_the_cache_costs_nothing_and_is_not_counted(make_client):
    first, second = signed_in(make_client, "a@example.com"), signed_in(make_client, "b@example.com")
    assert summary(first).json()["ai"]["remaining"] == 0
    again = summary(second).json()
    assert again["trace"]["cache_hit"] is True
    assert again["ai"]["remaining"] == 1


def test_each_account_has_its_own_allowance(make_client):
    first, second = signed_in(make_client, "a@example.com"), signed_in(make_client, "b@example.com")
    summary(first, "what bait for crappie")
    assert summary(first, "what do sand bass eat").status_code == 429
    assert summary(second, "what do sand bass eat").status_code == 200


def test_the_allowance_starts_again_the_next_day(make_client, monkeypatch):
    c = signed_in(make_client)
    monkeypatch.setattr(ai_quota, "today", lambda: date(2026, 10, 18))
    summary(c, "what bait for crappie")
    assert summary(c, "what do sand bass eat").status_code == 429

    monkeypatch.setattr(ai_quota, "today", lambda: date(2026, 10, 19))
    assert summary(c, "what do sand bass eat").status_code == 200


MANY = [
    "what bait for crappie",
    "what lure for largemouth",
    "what do bluegill eat",
    "what do sand bass eat",
    "what rod for stripers",
]


def test_admins_are_not_limited(make_client, db_session):
    c = signed_in(make_client, "owner@example.com")
    make_admin(db_session, "owner@example.com")
    for q in MANY:
        resp = summary(c, q)
        assert resp.status_code == 200
        assert resp.json()["ai"] == {**UNLIMITED, "plus": False}


# The product owner, 2026-11-12: Plus asks the AI as often as it likes.
def test_plus_is_not_limited(make_client, db_session):
    c = signed_in(make_client, "plus@example.com")
    make_plus(db_session, "plus@example.com")
    for q in MANY:
        resp = summary(c, q)
        assert resp.status_code == 200
        assert resp.json()["ai"] == {**UNLIMITED, "plus": True}


def test_plus_that_has_run_out_is_a_free_account_again(make_client, db_session):
    c = signed_in(make_client, "lapsed@example.com")
    make_plus(db_session, "lapsed@example.com", days=-1)
    assert c.get("/api/ask/allowance").json() == FREE


def test_an_admin_gives_plus_and_takes_it_away(make_client, db_session):
    owner = signed_in(make_client, "owner@example.com")
    make_admin(db_session, "owner@example.com")
    angler = signed_in(make_client, "angler@example.com")
    uid = db_session.scalar(select(User.id).where(User.email == "angler@example.com"))

    given = owner.patch(f"/api/admin/users/{uid}", json={"plus_days": 30})
    assert given.status_code == 200 and given.json()["plus_until"]
    assert angler.get("/api/ask/allowance").json()["plus"] is True

    taken = owner.patch(f"/api/admin/users/{uid}", json={"plus_days": 0})
    assert taken.status_code == 200 and taken.json()["plus_until"] is None
    assert angler.get("/api/ask/allowance").json() == FREE


def test_the_last_summary_cannot_be_taken_twice(db_session, make_client):
    """reserve() is one conditional UPDATE: at the limit it takes nothing."""
    signed_in(make_client)
    user = db_session.scalar(select(User))
    day = date(2026, 10, 18)
    assert [ai_quota.reserve(db_session, user, day) for _ in range(3)] == [True, False, False]
    assert ai_quota.allowance(db_session, user, day).used == 1


def test_a_summary_from_another_site_is_refused(make_client):
    c = signed_in(make_client)
    resp = c.post("/api/ask/summary", json=QUESTION, headers={"Origin": "https://evil.example"})
    assert resp.status_code == 403
