"""/api/pins/{id}/like and /comments, /api/leaderboard, /api/anglers, /api/alerts (docs/adr/0054)."""
from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth_deps import optional_user, require_user, same_origin
from app.api.deps import get_db
from app.api.params import DbId
from app.api.pins import CountyParam, StateParam, _throttle, _verified
from app.core.security import RateLimiter
from app.models.community import PIN_PUBLISHED, CatchPin, PinComment, SpeciesAlert, User
from app.schemas.social import (
    AlertIn,
    AlertOut,
    AlertsOut,
    AnglerOut,
    CommentAuthorOut,
    CommentIn,
    CommentOut,
    CommentReportIn,
    CommentReportOut,
    LeaderboardOut,
    LikeOut,
    StandingOut,
    UnsubscribeIn,
    UnsubscribeOut,
)
from app.services import alerts as alert_service
from app.services import pins as pin_service
from app.services import social
from app.services.pins import SPECIES_LABELS, PinError

router = APIRouter(tags=["social"], dependencies=[Depends(same_origin)])

like_by_user = RateLimiter(limit=240, window_seconds=60 * 60)
comment_by_user = RateLimiter(limit=40, window_seconds=60 * 60)
report_by_user = RateLimiter(limit=20, window_seconds=60 * 60)


def _raise(exc: PinError) -> NoReturn:
    raise HTTPException(status_code=exc.status, detail=exc.message) from exc


def _pin(db: Session, pin_id: int, user: User | None) -> CatchPin:
    try:
        return pin_service.get_visible_pin(db, pin_id, user)
    except PinError as exc:
        _raise(exc)


def _like_out(db: Session, pin: CatchPin, user: User) -> LikeOut:
    s = social.counts(db, [pin.id], user)[pin.id]
    return LikeOut(liked=s.liked, like_count=s.likes)


@router.post("/pins/{pin_id}/like", response_model=LikeOut)
def like_pin(pin_id: DbId, user: User = Depends(require_user), db: Session = Depends(get_db)) -> LikeOut:
    pin = _pin(db, pin_id, user)
    _verified(user)
    _throttle(like_by_user, user)
    try:
        social.like(db, pin, user)
        db.commit()
    except PinError as exc:
        db.rollback()
        _raise(exc)
    except IntegrityError:
        # Two taps raced; the first one counted.
        db.rollback()
    return _like_out(db, pin, user)


@router.delete("/pins/{pin_id}/like", response_model=LikeOut)
def unlike_pin(pin_id: DbId, user: User = Depends(require_user), db: Session = Depends(get_db)) -> LikeOut:
    pin = _pin(db, pin_id, user)
    social.unlike(db, pin, user)
    db.commit()
    return _like_out(db, pin, user)


def _comment_out(comment: PinComment, pin: CatchPin, user: User | None) -> CommentOut:
    return CommentOut(
        id=comment.id,
        body=comment.body,
        created_at=comment.created_at,
        author=CommentAuthorOut(id=comment.user.id, display_name=comment.user.display_name),
        status=comment.status,
        is_mine=user is not None and user.id == comment.user_id,
        can_delete=social.can_delete(comment, pin, user),
        can_report=user is not None and user.id != comment.user_id and comment.status == PIN_PUBLISHED,
    )


@router.get("/pins/{pin_id}/comments", response_model=list[CommentOut])
def list_comments(pin_id: DbId, user: User | None = Depends(optional_user), db: Session = Depends(get_db)) -> list[CommentOut]:
    pin = _pin(db, pin_id, user)
    return [_comment_out(c, pin, user) for c in social.comments_of(db, pin, user)]


@router.post("/pins/{pin_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(pin_id: DbId, payload: CommentIn, user: User = Depends(require_user), db: Session = Depends(get_db)) -> CommentOut:
    pin = _pin(db, pin_id, user)
    _verified(user)
    _throttle(comment_by_user, user)
    try:
        comment = social.add_comment(db, pin, user, payload.body)
    except PinError as exc:
        db.rollback()
        _raise(exc)
    db.commit()
    db.refresh(comment)
    return _comment_out(comment, pin, user)


@router.delete("/pins/{pin_id}/comments/{comment_id}", status_code=204, response_class=Response)
def delete_comment(pin_id: DbId, comment_id: DbId, user: User = Depends(require_user), db: Session = Depends(get_db)) -> Response:
    pin = _pin(db, pin_id, user)
    try:
        social.delete_comment(db, social.comment_of(db, pin, comment_id), pin, user)
    except PinError as exc:
        db.rollback()
        _raise(exc)
    db.commit()
    return Response(status_code=204)


@router.post("/pins/{pin_id}/comments/{comment_id}/reports", response_model=CommentReportOut, status_code=201)
def report_comment(
    pin_id: DbId, comment_id: DbId, payload: CommentReportIn, user: User = Depends(require_user), db: Session = Depends(get_db)
) -> CommentReportOut:
    pin = _pin(db, pin_id, user)
    _verified(user)
    _throttle(report_by_user, user)
    try:
        hidden = social.report_comment(db, social.comment_of(db, pin, comment_id), user, payload.reason)
    except PinError as exc:
        db.rollback()
        _raise(exc)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="You've already reported this comment.") from None
    db.commit()
    return CommentReportOut(received=True, hidden=hidden)


@router.get("/leaderboard", response_model=LeaderboardOut)
def leaderboard(
    metric: str = social.CATCHES,
    period: str = "30d",
    state: str | None = StateParam,
    county: str | None = CountyParam,
    user: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
) -> LeaderboardOut:
    try:
        top, me = social.leaderboard(db, user, metric, period, state, county)
    except PinError as exc:
        _raise(exc)

    def out(s: social.Standing) -> StandingOut:
        return StandingOut(rank=s.rank, user_id=s.user_id, display_name=s.display_name, value=s.value, is_me=user is not None and s.user_id == user.id)

    return LeaderboardOut(metric=metric, period=period, entries=[out(s) for s in top], me=out(me) if me else None)


@router.get("/anglers/{user_id}", response_model=AnglerOut)
def angler(user_id: DbId, db: Session = Depends(get_db)) -> AnglerOut:
    try:
        a = social.angler(db, user_id)
    except PinError as exc:
        _raise(exc)
    return AnglerOut(id=a.id, display_name=a.display_name, joined_at=a.joined_at, catches=a.catches, confirmed=a.confirmed, likes=a.likes)  # type: ignore[arg-type]


# ----------------------------------------------------------------- alerts


def _alert_out(a: SpeciesAlert) -> AlertOut:
    return AlertOut(
        id=a.id,
        species_slug=a.species_slug,
        species_label=SPECIES_LABELS.get(a.species_slug, a.species_slug),
        place=a.place,
        radius_miles=a.radius_miles,
        created_at=a.created_at,
        last_sent_at=a.last_sent_at,
    )


@router.get("/alerts", response_model=AlertsOut)
def my_alerts(user: User = Depends(require_user), db: Session = Depends(get_db)) -> AlertsOut:
    return AlertsOut(
        alerts=[_alert_out(a) for a in alert_service.alerts_of(db, user)],
        email=user.email,
        email_confirmed=alert_service.can_be_emailed(user),
        sending=alert_service.sending(),
        max_alerts=alert_service.MAX_PER_USER,
        min_radius=alert_service.MIN_RADIUS,
        max_radius=alert_service.MAX_RADIUS,
    )


@router.post("/alerts", response_model=AlertOut, status_code=201)
def create_alert(payload: AlertIn, user: User = Depends(require_user), db: Session = Depends(get_db)) -> AlertOut:
    try:
        alert = alert_service.create(
            db, user, payload.species_slug, payload.latitude, payload.longitude, payload.place, payload.radius_miles, payload.lang
        )
    except PinError as exc:
        db.rollback()
        _raise(exc)
    db.commit()
    db.refresh(alert)
    return _alert_out(alert)


@router.delete("/alerts/{alert_id}", status_code=204, response_class=Response)
def delete_alert(alert_id: DbId, user: User = Depends(require_user), db: Session = Depends(get_db)) -> Response:
    try:
        alert_service.delete(db, user, alert_id)
    except PinError as exc:
        _raise(exc)
    db.commit()
    return Response(status_code=204)


@router.post("/alerts/unsubscribe", response_model=UnsubscribeOut)
def unsubscribe(payload: UnsubscribeIn, db: Session = Depends(get_db)) -> UnsubscribeOut:
    """A button on /unsubscribe, not the emailed link itself: mail scanners
    open links, and a GET that deleted the alert would be undone by them."""
    try:
        alert = alert_service.unsubscribe(db, payload.token)
        out = UnsubscribeOut(species_label=SPECIES_LABELS.get(alert.species_slug, alert.species_slug), place=alert.place)
    except PinError as exc:
        _raise(exc)
    db.commit()
    return out

