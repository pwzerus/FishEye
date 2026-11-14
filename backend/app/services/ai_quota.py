"""The daily allowance of AI answers (docs/adr/0023).

Searching the guides is free and open to everyone (api/ask.py). An AI answer
costs a model call, so it needs an account and is limited to
`ai_summaries_per_day` per UTC day. FishEye Plus accounts are not limited,
nor are admins: they are the ones testing it.

The count is kept per email address, as a one-way key, for KEEP_DAYS days
(models/community.AiUsage): deleting the account and signing up again with
the same address the same day finds the day's answers already used (the
product owner, 2026-11-13).

A summary is reserved before the model is called and given back if no
model-written answer comes of it (the model was unreachable, or its answer
failed validation and the guides were quoted instead). Reserving first is
what keeps two summaries requested at the same moment from both getting the
last one: the reservation is a single conditional UPDATE, which the
database applies to one request at a time.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.community import AiUsage, User


@dataclass(frozen=True)
class Allowance:
    limit: int | None  # None: unlimited (Plus, admins)
    used: int
    plus: bool = False

    @property
    def remaining(self) -> int | None:
        return None if self.limit is None else max(0, self.limit - self.used)


# How long a day's count is kept, account or no account.
KEEP_DAYS = 30


def today() -> date:
    return datetime.now(UTC).date()


def email_key(email: str) -> str:
    """A one-way key for an email address: the same address, however it is
    capitalised or spaced, always gives the same key, and the key doesn't
    give the address back."""
    return hashlib.sha256(f"fisheye-ai-usage:{email.strip().lower()}".encode()).hexdigest()


def _limit_for(user: User) -> int | None:
    return None if user.is_admin or user.is_plus else get_settings().ai_summaries_per_day


def _used(db: Session, user: User, day: date) -> int:
    used = db.scalar(select(AiUsage.used).where(AiUsage.email_key == email_key(user.email), AiUsage.day == day))
    return used or 0


def allowance(db: Session, user: User, day: date | None = None) -> Allowance:
    day = day or today()
    return Allowance(_limit_for(user), _used(db, user, day), plus=user.is_plus)


def _ensure_row(db: Session, key: str, day: date) -> None:
    if db.scalar(select(AiUsage.id).where(AiUsage.email_key == key, AiUsage.day == day)):
        return
    try:
        with db.begin_nested():
            db.add(AiUsage(email_key=key, day=day, used=0))
    except IntegrityError:
        pass  # another request created it first; the row is there either way


def reserve(db: Session, user: User, day: date | None = None) -> bool:
    """Take one summary from today's allowance. False if none are left."""
    day = day or today()
    key = email_key(user.email)
    # Counts older than KEEP_DAYS go: nothing needs them after that.
    db.execute(delete(AiUsage).where(AiUsage.day < day - timedelta(days=KEEP_DAYS)))
    _ensure_row(db, key, day)
    limit = _limit_for(user)
    stmt = update(AiUsage).where(AiUsage.email_key == key, AiUsage.day == day)
    if limit is not None:
        stmt = stmt.where(AiUsage.used < limit)
    taken = db.execute(stmt.values(used=AiUsage.used + 1)).rowcount == 1
    db.commit()
    return taken


def give_back(db: Session, user: User, day: date) -> None:
    db.execute(
        update(AiUsage)
        .where(AiUsage.email_key == email_key(user.email), AiUsage.day == day, AiUsage.used > 0)
        .values(used=AiUsage.used - 1)
    )
    db.commit()
