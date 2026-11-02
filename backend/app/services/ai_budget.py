"""A ceiling on what the AI model costs in a calendar month (UTC).

The other limits count requests (per account, per visitor, per day) and live
partly in memory, so they say nothing about dollars and reset on a restart.
This one counts dollars, in the database, around every call to a paid model:
summaries and the advisor, retries included, admins included. At the ceiling
the model isn't called, and both features already know what to do when it
can't be: the guides and the plain-language plan are shown as they are.

The figure is an estimate from token counts and list prices (llm/anthropic.py),
and calls already under way can finish, so it can overshoot by a few cents. It
protects against heavy use of the site. It can't protect against someone who
steals the API key, who never comes through here: for that, set a limit in the
Anthropic console too.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.community import AiSpend
from app.services.llm import get_provider
from app.services.llm.base import LLMProvider, LLMResponse, LLMUnavailable

logger = logging.getLogger(__name__)

PAUSED = "AI summaries are paused until next month. The fish guides, the map and Ask's answers from the guides still work."


def this_month() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def budget() -> float:
    return get_settings().ai_monthly_budget_usd


def available() -> bool:
    """Is a paid model set up and allowed to spend? Without one the summaries
    could only restate the guides, so the page doesn't offer them."""
    try:
        return budget() > 0 and isinstance(get_provider(), BudgetedProvider)
    except NotImplementedError:  # LLM_PROVIDER names a vendor we don't have
        return False


def spent(db: Session, month: str | None = None) -> float:
    return db.scalar(select(AiSpend.usd).where(AiSpend.month == (month or this_month()))) or 0.0


def exhausted(db: Session) -> bool:
    return spent(db) >= budget()


def record(db: Session, cost: float, month: str | None = None) -> None:
    """Adds in one UPDATE, so two calls at once both count."""
    month = month or this_month()
    change = update(AiSpend).where(AiSpend.month == month).values(usd=AiSpend.usd + cost, calls=AiSpend.calls + 1)
    if db.execute(change).rowcount == 0:
        try:
            with db.begin_nested():
                db.add(AiSpend(month=month, usd=cost, calls=1))
        except IntegrityError:  # another call made the row first
            db.execute(change)
    db.commit()


class BudgetedProvider(LLMProvider):
    """A paid model, with the month's ceiling around it."""

    def __init__(self, inner: LLMProvider, sessions: Callable[[], Session] = SessionLocal) -> None:
        self._inner = inner
        self._sessions = sessions
        self.name = inner.name
        self.model = getattr(inner, "model", None)

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        try:
            with self._sessions() as db:
                over = exhausted(db)
        except Exception as exc:
            # Money at stake: if the spend can't be read, don't spend.
            logger.error("AI budget couldn't be read: %s", exc)
            raise LLMUnavailable("AI budget couldn't be read") from exc
        if over:
            logger.warning("AI budget of $%.2f reached for %s; the model isn't being called.", budget(), this_month())
            raise LLMUnavailable("monthly AI budget reached")
        response = self._inner.complete(system_prompt, user_prompt)
        try:
            with self._sessions() as db:
                record(db, response.estimated_cost_usd)
        except Exception as exc:
            logger.error("AI spend of $%.5f couldn't be recorded: %s", response.estimated_cost_usd, exc)
        return response
