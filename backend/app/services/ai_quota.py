"""The daily allowance of AI summaries per account (docs/adr/0023).

Searching the guides is free and open to everyone (api/ask.py). Turning the
passages found into a written answer costs a model call, so that step needs
an account and is limited to `ai_summaries_per_day` per account per UTC day.
Admins are not limited: they are the ones testing it.

A summary is reserved before the model is called and given back if no
model-written answer comes of it (the model was unreachable, or its answer
failed validation and the guides were quoted instead). Reserving first is
what keeps two summaries requested at the same moment from both getting the
last one: the reservation is a single conditional UPDATE, which the
database applies to one request at a time.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.community import AiUsage, User


@dataclass(frozen=True)
class Allowance:
    limit: int | None  # None: unlimited (admins)
    used: int

    @property
    def remaining(self) -> int | None:
        return None if self.limit is None else max(0, self.limit - self.used)


def today() -> date:
    return datetime.now(UTC).date()


def _limit_for(user: User) -> int | None:
    return None if user.is_admin else get_settings().ai_summaries_per_day


def _used(db: Session, user: User, day: date) -> int:
    used = db.scalar(select(AiUsage.used).where(AiUsage.user_id == user.id, AiUsage.day == day))
    return used or 0


def allowance(db: Session, user: User, day: date | None = None) -> Allowance:
    day = day or today()
    return Allowance(_limit_for(user), _used(db, user, day))


def _ensure_row(db: Session, user: User, day: date) -> None:
    if db.scalar(select(AiUsage.id).where(AiUsage.user_id == user.id, AiUsage.day == day)):
        return
    try:
        with db.begin_nested():
            db.add(AiUsage(user_id=user.id, day=day, used=0))
    except IntegrityError:
        pass  # another request created it first; the row is there either way


def reserve(db: Session, user: User, day: date | None = None) -> bool:
    """Take one summary from today's allowance. False if none are left."""
    day = day or today()
    _ensure_row(db, user, day)
    limit = _limit_for(user)
    stmt = update(AiUsage).where(AiUsage.user_id == user.id, AiUsage.day == day)
    if limit is not None:
        stmt = stmt.where(AiUsage.used < limit)
    taken = db.execute(stmt.values(used=AiUsage.used + 1)).rowcount == 1
    db.commit()
    return taken


def give_back(db: Session, user: User, day: date) -> None:
    db.execute(
        update(AiUsage)
        .where(AiUsage.user_id == user.id, AiUsage.day == day, AiUsage.used > 0)
        .values(used=AiUsage.used - 1)
    )
    db.commit()
