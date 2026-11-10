"""Page visits, counted per day (services/visits.py)."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PageVisit(Base):
    """How many times a page was opened on a day, and where from.

    A count and nothing else: no address, no cookie, no account, nothing
    that tells one visitor from another. `source` is the site a link was
    followed from (a host name) or a campaign tag (?ref=reddit); "" when
    neither is known.
    """

    __tablename__ = "page_visits"
    __table_args__ = (UniqueConstraint("day", "path", "source", name="uq_page_visits_day_path_source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    path: Mapped[str] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(String(64), default="")
    count: Mapped[int] = mapped_column(Integer, default=0)
