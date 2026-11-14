"""The month's ceiling on what the AI model costs (services/ai_budget.py)."""
from __future__ import annotations

import pytest
from sqlalchemy.orm import sessionmaker

from app.models.community import AiSpend
from app.services import ai_budget
from app.services.llm import reset_provider_cache
from app.services.llm.base import LLMProvider, LLMResponse, LLMUnavailable
from tests.conftest import make_admin, signup


class Paid(LLMProvider):
    name = "paid"
    model = "test"

    def __init__(self, cost=0.01):
        self.cost = cost
        self.calls = 0

    def complete(self, system_prompt, user_prompt):
        self.calls += 1
        return LLMResponse(text="{}", provider=self.name, model=self.model, prompt_tokens=10, completion_tokens=10, estimated_cost_usd=self.cost, latency_ms=0.0)


@pytest.fixture
def sessions(db_session):
    return sessionmaker(bind=db_session.get_bind())


def test_it_is_ten_dollars_unless_set_otherwise():
    assert ai_budget.budget() == 10.0


def test_spending_adds_up_and_is_kept(sessions):
    p = ai_budget.BudgetedProvider(Paid(0.25), sessions)
    p.complete("s", "u")
    p.complete("s", "u")
    with sessions() as db:
        row = db.get(AiSpend, 1)
        assert (row.usd, row.calls, row.month) == (0.5, 2, ai_budget.this_month())


def test_at_the_ceiling_the_model_isnt_called(sessions):
    inner = Paid(6.0)
    p = ai_budget.BudgetedProvider(inner, sessions)
    p.complete("s", "u")
    p.complete("s", "u")  # 6 is under 10; 12 is over
    with pytest.raises(LLMUnavailable):
        p.complete("s", "u")
    assert inner.calls == 2


def test_a_new_month_starts_again(sessions):
    with sessions() as db:
        ai_budget.record(db, 50.0, month="2020-01")
    inner = Paid()
    ai_budget.BudgetedProvider(inner, sessions).complete("s", "u")
    assert inner.calls == 1


def test_a_budget_of_zero_turns_it_off(sessions, monkeypatch):
    monkeypatch.setattr(ai_budget, "budget", lambda: 0.0)
    inner = Paid()
    with pytest.raises(LLMUnavailable):
        ai_budget.BudgetedProvider(inner, sessions).complete("s", "u")
    assert inner.calls == 0


def test_if_the_spend_cant_be_read_nothing_is_spent():
    def broken():
        raise RuntimeError("database down")

    inner = Paid()
    with pytest.raises(LLMUnavailable):
        ai_budget.BudgetedProvider(inner, broken).complete("s", "u")
    assert inner.calls == 0


def test_a_failed_call_costs_nothing(sessions):
    class Down(Paid):
        def complete(self, *_):
            raise LLMUnavailable("down")

    with pytest.raises(LLMUnavailable):
        ai_budget.BudgetedProvider(Down(), sessions).complete("s", "u")
    with sessions() as db:
        assert ai_budget.spent(db) == 0.0


def test_the_real_provider_comes_wrapped(monkeypatch):
    from app.core.config import get_settings
    from app.services.llm import get_provider

    s = get_settings()
    monkeypatch.setattr(s, "llm_provider", "anthropic")
    monkeypatch.setattr(s, "llm_api_key", "test-key")
    reset_provider_cache()
    try:
        assert isinstance(get_provider(), ai_budget.BudgetedProvider)
    finally:
        reset_provider_cache()


def test_summaries_are_offered_only_with_a_paid_model_allowed_to_spend(make_client, monkeypatch):
    from app.core.config import get_settings

    c = make_client()

    def enabled():
        return c.get("/api/ask/allowance").json()["enabled"]

    s = get_settings()
    reset_provider_cache()
    try:
        monkeypatch.setattr(s, "llm_provider", "mock")
        assert enabled() is False

        monkeypatch.setattr(s, "llm_provider", "anthropic")
        monkeypatch.setattr(s, "llm_api_key", None)
        reset_provider_cache()
        assert enabled() is False  # named, but no key: the mock answers

        monkeypatch.setattr(s, "llm_api_key", "test-key")
        reset_provider_cache()
        assert enabled() is True

        monkeypatch.setattr(s, "ai_monthly_budget_usd", 0.0)
        assert enabled() is False  # turned off on purpose

        monkeypatch.setattr(s, "llm_provider", "openai")
        reset_provider_cache()
        monkeypatch.setattr(s, "ai_monthly_budget_usd", 10.0)
        assert enabled() is False  # a vendor we don't have doesn't break the search
    finally:
        reset_provider_cache()


def test_a_summary_at_the_ceiling_says_so_and_uses_no_allowance(make_client, db_session, monkeypatch):
    c = make_client()
    signup(c)
    db_session.add(AiSpend(month=ai_budget.this_month(), usd=10.0, calls=1000))
    db_session.commit()
    r = c.post("/api/ask/summary", json={"question": "what bait for largemouth bass"})
    assert r.status_code == 503 and "paused" in r.json()["detail"]
    assert c.get("/api/ask/allowance").json()["remaining"] == 3  # the day's three, untouched
    # Searching the guides costs nothing and carries on.
    assert c.post("/api/ask", json={"question": "what bait for largemouth bass"}).json()["citations"]


def test_admins_see_the_months_spend_and_are_held_to_it(make_client, db_session):
    a = make_client()
    signup(a, email="boss@example.com", name="Head Boss")
    make_admin(db_session, "boss@example.com")
    db_session.add(AiSpend(month=ai_budget.this_month(), usd=10.5, calls=1000))
    db_session.commit()
    stats = a.get("/api/admin/stats").json()
    assert stats["ai_spent_usd"] == 10.5 and stats["ai_budget_usd"] == 10.0
    assert a.post("/api/ask/summary", json={"question": "what bait for largemouth bass"}).status_code == 503
