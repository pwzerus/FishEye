"""What anglers do with each other's catches: likes, comments, leaderboards (docs/adr/0054).

Only on public, published catches: a private catch has nobody to like it, and
one a moderator hid isn't there to discuss. Like a catch, this is user content
that never reaches the guides or the official tiers.

A leaderboard counts public catches only and shows the name those catches
already show. Someone can leave them from their account page (hide_from_rankings).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.types import utcnow
from app.models.community import (
    PIN_HIDDEN,
    PIN_PUBLISHED,
    REPORT_OPEN,
    USER_ACTIVE,
    VISIBILITY_PUBLIC,
    CatchPin,
    CommentReport,
    PinComment,
    PinLike,
    User,
)
from app.services import audit, fish_id, word_filter
from app.services.pins import REPORT_REASONS, PinError, _text

MAX_COMMENT = 500
MAX_COMMENTS_SHOWN = 200
RANK_SIZE = 10
# Enough to place anyone in a state; a place can't have more anglers than this in view.
RANK_SCAN = 2000

CATCHES, SHARES, ACTIVE, LIKES = "catches", "shares", "active", "likes"
METRICS = (CATCHES, SHARES, ACTIVE, LIKES)
PERIODS = {"30d": 30, "all": None}


@dataclass(frozen=True)
class Social:
    likes: int = 0
    comments: int = 0
    liked: bool = False


def counts(db: Session, pin_ids: list[int], user: User | None) -> dict[int, Social]:
    """Likes and comments of many catches at once, for a list of them."""
    if not pin_ids:
        return {}
    likes = dict(db.execute(select(PinLike.pin_id, func.count(PinLike.id)).where(PinLike.pin_id.in_(pin_ids)).group_by(PinLike.pin_id)).all())
    comments = dict(
        db.execute(
            select(PinComment.pin_id, func.count(PinComment.id))
            .where(PinComment.pin_id.in_(pin_ids), PinComment.status == PIN_PUBLISHED)
            .group_by(PinComment.pin_id)
        ).all()
    )
    mine = set(db.scalars(select(PinLike.pin_id).where(PinLike.pin_id.in_(pin_ids), PinLike.user_id == user.id))) if user else set()
    return {i: Social(int(likes.get(i, 0)), int(comments.get(i, 0)), i in mine) for i in pin_ids}


def _public(pin: CatchPin) -> None:
    if pin.visibility != VISIBILITY_PUBLIC or pin.status != PIN_PUBLISHED:
        raise PinError(409, "Only a public catch can be liked or commented on.")


# ----------------------------------------------------------------- likes


def like(db: Session, pin: CatchPin, user: User) -> None:
    _public(pin)
    if pin.user_id == user.id:
        raise PinError(422, "You can't like your own catch.")
    if db.scalar(select(PinLike.id).where(PinLike.pin_id == pin.id, PinLike.user_id == user.id)) is None:
        db.add(PinLike(pin_id=pin.id, user_id=user.id))


def unlike(db: Session, pin: CatchPin, user: User) -> None:
    found = db.scalar(select(PinLike).where(PinLike.pin_id == pin.id, PinLike.user_id == user.id))
    if found is not None:
        db.delete(found)


# -------------------------------------------------------------- comments


def comments_of(db: Session, pin: CatchPin, viewer: User | None) -> list[PinComment]:
    """Oldest first, as a conversation reads. Moderators also see what's hidden."""
    q = select(PinComment).options(selectinload(PinComment.user)).where(PinComment.pin_id == pin.id)
    if viewer is None or not viewer.is_admin:
        q = q.where(PinComment.status == PIN_PUBLISHED)
    return list(db.scalars(q.order_by(PinComment.created_at, PinComment.id).limit(MAX_COMMENTS_SHOWN)))


def add_comment(db: Session, pin: CatchPin, user: User, body: str) -> PinComment:
    _public(pin)
    text = _text(body, MAX_COMMENT)
    if not text:
        raise PinError(422, "Write something first.")
    if word_filter.blocked_word(text):
        raise PinError(422, "The comment includes a word FishEye doesn't allow.")
    comment = PinComment(pin_id=pin.id, user_id=user.id, body=text)
    db.add(comment)
    db.flush()
    return comment


def can_delete(comment: PinComment, pin: CatchPin, user: User | None) -> bool:
    """Whoever wrote it, whoever's catch it's under, and the moderators."""
    return user is not None and (user.id in (comment.user_id, pin.user_id) or user.is_admin)


def comment_of(db: Session, pin: CatchPin, comment_id: int) -> PinComment:
    comment = db.get(PinComment, comment_id)
    if comment is None or comment.pin_id != pin.id:
        raise PinError(404, "No such comment.")
    return comment


def delete_comment(db: Session, comment: PinComment, pin: CatchPin, user: User) -> None:
    if not can_delete(comment, pin, user):
        raise PinError(403, "Only the person who wrote it, or whose catch it's under, can delete it.")
    if user.id != comment.user_id:
        audit.record(db, user, "comment.deleted", "comment", comment.id, pin=pin.id)
    db.delete(comment)


def report_comment(db: Session, comment: PinComment, reporter: User, reason: str) -> bool:
    """Files a report. Returns True if this report hid the comment."""
    if reason not in REPORT_REASONS:
        raise PinError(422, "Pick a reason.")
    if comment.user_id == reporter.id:
        raise PinError(422, "You can't report your own comment.")
    if comment.status != PIN_PUBLISHED:
        raise PinError(404, "No such comment.")
    if db.scalar(select(CommentReport.id).where(CommentReport.comment_id == comment.id, CommentReport.reporter_id == reporter.id)) is not None:
        raise PinError(409, "You've already reported this comment. A moderator will look at it.")
    db.add(CommentReport(comment_id=comment.id, reporter_id=reporter.id, reason=reason))
    db.flush()
    open_reports = db.scalar(
        select(func.count(CommentReport.id)).where(CommentReport.comment_id == comment.id, CommentReport.status == REPORT_OPEN)
    ) or 0
    if open_reports >= get_settings().report_auto_hide_threshold:
        comment.status = PIN_HIDDEN
        audit.record(db, None, "comment.auto_hidden", "comment", comment.id, open_reports=open_reports)
        return True
    return False


# ---------------------------------------------------------- leaderboards


@dataclass(frozen=True)
class Standing:
    rank: int
    user_id: int
    display_name: str
    value: int


def _board(metric: str, since, state: str | None, county: str | None) -> Select:
    if metric == LIKES:
        value = func.count(PinLike.id)
        q = select(User.id, User.display_name, value).join(CatchPin, CatchPin.user_id == User.id).join(PinLike, PinLike.pin_id == CatchPin.id)
        if since is not None:
            q = q.where(PinLike.created_at >= since)
    else:
        if metric == ACTIVE:
            # Days out on the water: the day caught, or the day shared.
            value = func.count(func.distinct(func.coalesce(CatchPin.caught_on, func.date(CatchPin.created_at))))
        else:
            value = func.count(CatchPin.id)
        q = select(User.id, User.display_name, value).join(CatchPin, CatchPin.user_id == User.id)
        if since is not None:
            q = q.where(CatchPin.created_at >= since)
        if metric == CATCHES:
            # A fish the photo check backed, not a post saying so.
            q = q.where(CatchPin.species_check.in_((fish_id.CONFIRMED, fish_id.GROUP)))
    q = q.where(
        CatchPin.visibility == VISIBILITY_PUBLIC,
        CatchPin.status == PIN_PUBLISHED,
        User.status == USER_ACTIVE,
        User.hide_from_rankings.is_(False),
    )
    if state:
        q = q.where(CatchPin.state_code == state.upper())
    if county:
        q = q.where(CatchPin.county_geoid == county)
    return q.group_by(User.id, User.display_name).order_by(value.desc(), User.id).limit(RANK_SCAN)


def leaderboard(
    db: Session, viewer: User | None, metric: str, period: str, state: str | None, county: str | None
) -> tuple[list[Standing], Standing | None]:
    """The top of a place's board, and where the viewer stands on it. Equal
    values share a rank: nobody is behind someone with the same count."""
    if metric not in METRICS:
        raise PinError(422, "No such leaderboard.")
    if period not in PERIODS:
        raise PinError(422, "No such period.")
    days = PERIODS[period]
    since = utcnow() - timedelta(days=days) if days else None
    rows = db.execute(_board(metric, since, state, county)).all()
    standings: list[Standing] = []
    rank = 0
    previous = None
    for i, (user_id, name, value) in enumerate(rows, start=1):
        if value != previous:
            rank, previous = i, value
        standings.append(Standing(rank, user_id, name, int(value)))
    me = next((s for s in standings if viewer is not None and s.user_id == viewer.id), None)
    return standings[:RANK_SIZE], me


# --------------------------------------------------------------- anglers


@dataclass(frozen=True)
class Angler:
    id: int
    display_name: str
    joined_at: object
    catches: int
    confirmed: int
    likes: int


def angler(db: Session, user_id: int) -> Angler:
    """What's public about someone: the name and what they've shared."""
    user = db.get(User, user_id)
    if user is None or user.status != USER_ACTIVE:
        raise PinError(404, "No such angler.")
    public = (CatchPin.user_id == user.id) & (CatchPin.visibility == VISIBILITY_PUBLIC) & (CatchPin.status == PIN_PUBLISHED)
    shared = db.scalar(select(func.count(CatchPin.id)).where(public)) or 0
    if shared == 0:
        raise PinError(404, "No such angler.")
    confirmed = db.scalar(select(func.count(CatchPin.id)).where(public, CatchPin.species_check.in_((fish_id.CONFIRMED, fish_id.GROUP)))) or 0
    likes = db.scalar(select(func.count(PinLike.id)).join(CatchPin, PinLike.pin_id == CatchPin.id).where(public)) or 0
    return Angler(user.id, user.display_name, user.created_at, int(shared), int(confirmed), int(likes))
