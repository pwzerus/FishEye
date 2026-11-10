"""A visit counter that tells no visitor from another (docs/adr/0045).

The site's pages report each page opened (components/VisitCounter.tsx);
this adds one to that page's count for the day. Nothing is kept that could
pick out a person: no IP address, no cookie or other identifier, no
account, no full referring URL. What is kept is the day, the page, and the
site the link came from or a campaign tag, which is what promotion needs
to know: is anyone coming, to which page, and from where.

Pages are counted by their kind where the rest of the path is someone's
(a catch's id), so the table can't grow one row per catch.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from urllib.parse import urlsplit

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.types import utcnow
from app.models.visits import PageVisit

# Pages not worth counting: they're for staff or for one person's account.
_SKIPPED = ("/admin", "/account", "/reset-password", "/verify-email", "/api")
_SLUG = re.compile(r"^[a-z0-9-]{1,60}$")
_TAG = re.compile(r"[^a-z0-9._-]")


def clean_path(path: str | None) -> str | None:
    """The page, without its query or anything personal; None to skip."""
    if not path or not path.startswith("/"):
        return None
    path = path.split("?")[0].split("#")[0].rstrip("/") or "/"
    if any(path == p or path.startswith(p + "/") for p in _SKIPPED):
        return None
    if path == "/":
        return path
    parts = path.strip("/").split("/")
    if not all(_SLUG.match(p) for p in parts[:1]):
        return None
    if parts[0] == "fish" and len(parts) == 2 and _SLUG.match(parts[1]):
        return path  # a fish guide: public, and a few dozen of them
    if parts[0] == "community" and len(parts) == 2:
        return "/community/:id"
    if len(parts) > 1:
        return f"/{parts[0]}/…"
    return path


def clean_source(referrer: str | None, ref: str | None, own_host: str | None) -> str:
    """Where the visit came from: a campaign tag if the link had one, else
    the referring site's host name; "" for none or this site itself."""
    tag = _TAG.sub("", (ref or "").strip().lower())[:40]
    if tag:
        return f"ref:{tag}"
    if not referrer:
        return ""
    try:
        host = (urlsplit(referrer).hostname or "").lower()
    except ValueError:
        return ""
    host = host.removeprefix("www.")
    own = (own_host or "").lower().removeprefix("www.")
    if not host or host == own or host in ("localhost", "127.0.0.1"):
        return ""
    return host[:64]


def record(db: Session, path: str | None, referrer: str | None, ref: str | None, own_host: str | None) -> bool:
    """Count one visit. False when the page isn't one that is counted."""
    page = clean_path(path)
    if page is None:
        return False
    source = clean_source(referrer, ref, own_host)
    today = utcnow().date()
    match = (PageVisit.day == today, PageVisit.path == page, PageVisit.source == source)
    bump = update(PageVisit).where(*match).values(count=PageVisit.count + 1)
    if db.execute(bump).rowcount == 0:
        try:
            with db.begin_nested():
                db.add(PageVisit(day=today, path=page, source=source, count=1))
        except IntegrityError:
            # Another request made today's row first.
            db.execute(bump)
    return True


@dataclass
class Summary:
    days: int
    total: int
    by_day: list[tuple[date, int]]
    by_page: list[tuple[str, int]]
    by_source: list[tuple[str, int]]


def summary(db: Session, days: int = 30, top: int = 20) -> Summary:
    since = utcnow().date() - timedelta(days=days - 1)
    recent = PageVisit.day >= since
    total = db.scalar(select(func.coalesce(func.sum(PageVisit.count), 0)).where(recent)) or 0

    def grouped(column, limit: int | None) -> list:
        n = func.sum(PageVisit.count)
        stmt = select(column, n).where(recent).group_by(column)
        stmt = stmt.order_by(column) if limit is None else stmt.order_by(n.desc(), column).limit(limit)
        return [(key, int(count)) for key, count in db.execute(stmt).all()]

    return Summary(
        days=days,
        total=int(total),
        by_day=grouped(PageVisit.day, None),
        by_page=grouped(PageVisit.path, top),
        by_source=grouped(PageVisit.source, top),
    )


def as_text(s: Summary) -> str:
    lines = [f"FishEye visits, last {s.days} days: {s.total} page views (counts only, no visitors).", "", "By day:"]
    lines += [f"  {d:%Y-%m-%d}  {n}" for d, n in s.by_day] or ["  none"]
    lines += ["", "Top pages:"]
    lines += [f"  {n:>6}  {p}" for p, n in s.by_page] or ["  none"]
    lines += ["", "Where from (ref: is a tagged link):"]
    lines += [f"  {n:>6}  {src or '(direct, or not known)'}" for src, n in s.by_source] or ["  none"]
    return "\n".join(lines)
