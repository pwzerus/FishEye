"""Questions Ask couldn't answer, kept so the guides grow where people ask.

Ask is a search over reviewed guides (services/rag/ask.py): what it can't
answer is exactly what to write next. A miss is a search that found nothing
to show — no matching passage, a fish without a guide, only another state's
rules, or not a fishing question — recorded with its language and the state
and fish picked, and nothing that says who asked: no account, no IP, no
session. Email addresses, phone numbers and links are taken out of the
question before it is stored, and rows older than RETENTION_DAYS are deleted.

The same question on the same day for the same reason is one row with a
count, so a person retrying, or someone flooding the box, adds one row.
Recording never fails a search: a database error is logged and dropped.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.community import AskMiss
from app.services.ai_quota import today

log = logging.getLogger(__name__)

RETENTION_DAYS = 90
MAX_CHARS = 300

# The outcomes worth reading (rag/ask.py); "ok" and the model's own
# validation outcomes aren't misses.
MISS_OUTCOMES = frozenset({"no_match", "unguided_fish", "other_state", "off_topic"})

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
# Seven or more digits, allowing the usual separators: a phone number, not
# "a 10 lb catfish" or "2026".
_PHONE = re.compile(r"[+(]?\d(?:[\s().-]*\d){6,}")
_SPACE = re.compile(r"\s+")


def scrub(question: str) -> str:
    text = _EMAIL.sub("[email]", question)
    text = _URL.sub("[link]", text)
    text = _PHONE.sub("[number]", text)
    text = "".join(ch for ch in text if ch.isprintable())
    return _SPACE.sub(" ", text).strip()[:MAX_CHARS]


def record(
    db: Session,
    question: str,
    outcome: str,
    lang: str,
    state: str | None = None,
    species_slug: str | None = None,
    day: date | None = None,
) -> None:
    if outcome not in MISS_OUTCOMES:
        return
    text = scrub(question)
    if not text:
        return
    day = day or today()
    key = text.lower()
    try:
        bumped = db.execute(
            update(AskMiss)
            .where(AskMiss.day == day, AskMiss.outcome == outcome, AskMiss.key == key)
            .values(count=AskMiss.count + 1)
        ).rowcount
        if not bumped:
            try:
                with db.begin_nested():
                    db.add(
                        AskMiss(
                            day=day,
                            outcome=outcome,
                            key=key,
                            question=text,
                            lang=lang[:8],
                            state=state,
                            species_slug=species_slug,
                        )
                    )
            except IntegrityError:
                pass  # the same question at the same moment; one of them counts
        db.execute(delete(AskMiss).where(AskMiss.day < day - timedelta(days=RETENTION_DAYS)))
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        log.warning("couldn't record an Ask miss", exc_info=True)


@dataclass(frozen=True)
class MissRow:
    question: str
    outcome: str
    lang: str
    state: str | None
    species_slug: str | None
    count: int
    days: int
    last_day: date


def top(db: Session, days: int = 30, outcome: str | None = None, limit: int = 100) -> list[MissRow]:
    """The most asked of the last `days` days' misses, most asked first: one
    row per question and reason, its latest wording, language and picks."""
    since = today() - timedelta(days=days - 1)
    where = [AskMiss.day >= since]
    if outcome:
        where.append(AskMiss.outcome == outcome)
    total = func.sum(AskMiss.count).label("total")
    groups = db.execute(
        select(AskMiss.key, AskMiss.outcome, total, func.count().label("days"), func.max(AskMiss.day).label("last"))
        .where(*where)
        .group_by(AskMiss.key, AskMiss.outcome)
        .order_by(total.desc(), func.max(AskMiss.day).desc())
        .limit(limit)
    ).all()
    out = []
    for key, kind, count, n_days, last in groups:
        latest = db.scalar(
            select(AskMiss).where(AskMiss.key == key, AskMiss.outcome == kind, AskMiss.day == last)
        )
        out.append(
            MissRow(latest.question, kind, latest.lang, latest.state, latest.species_slug, int(count), n_days, last)
        )
    return out
