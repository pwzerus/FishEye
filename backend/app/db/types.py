"""Column types shared by the models."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    """Always stores naive UTC, always returns aware UTC.

    SQLite has no timezone support: an aware datetime goes in and a naive
    one comes out, and the first `expires_at > now()` comparison between
    the two raises. Session expiry and rate limits depend on exactly those
    comparisons, so the account tables normalise at the column instead of
    trusting every caller to remember.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime passed to a UTCDateTime column")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
