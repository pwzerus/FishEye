"""/api/admin — community moderation and account management (admin role).

Every change here writes an audit entry in the same transaction. Guards
against locking the site out of its own admin: an admin can't demote or
suspend themselves, and the last active admin can't be demoted, suspended
or deleted.
"""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.auth_deps import require_admin, same_origin
from app.api.deps import get_db
from app.api.params import DbId
from app.api.pins import summary_fields, waters_for
from app.db.types import utcnow
from app.models.community import (
    PIN_HIDDEN,
    PIN_PUBLISHED,
    PIN_REMOVED,
    FEEDBACK_NEW,
    REPORT_OPEN,
    REPORT_RESOLVED,
    ROLE_ADMIN,
    ROLE_USER,
    USER_ACTIVE,
    USER_SUSPENDED,
    VISIBILITY_PRIVATE,
    VISIBILITY_PUBLIC,
    AuditLog,
    CatchPin,
    Feedback,
    LakeReport,
    PinPhoto,
    PinReport,
    CommentReport,
    PinComment,
    User,
    UserSession,
)
from app.models.waterbody import Waterbody
from app.schemas.lake_reports import AdminLakeReportOut, LakeReportResolveIn
from app.schemas.feedback import AdminFeedbackOut, AdminFeedbackPage, FeedbackExportOut, FeedbackUpdateIn
from app.services import ai_budget, ask_misses
from app.services import feedback as feedback_service
from app.services import password_reset
from app.services import lake_reports as lake_report_service
from app.services.lake_reports import LakeReportError
from app.schemas.admin_community import (
    CommentReportGroupOut,
    CommentReportItemOut,
    CommentResolvedOut,
    ReportedCommentOut,
    AdminPinOut,
    AdminPinPage,
    AdminUserCatchOut,
    AdminUserDetailOut,
    AdminUserOut,
    AdminUserPage,
    AskMissOut,
    AuditOut,
    AuditPage,
    PinStatusIn,
    ReportGroupOut,
    ReportItemOut,
    ResetLinkIn,
    ResetLinkOut,
    ResolveIn,
    StatsOut,
    UserCountsOut,
    UserUpdateIn,
)
from app.schemas.pins import PinSummaryOut
from app.services import audit
from app.services import auth as auth_service
from app.services.auth import AuthError
from app.services import pins as pin_service
from app.services.media import get_store

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(same_origin)])

PAGE_SIZE = 25
MAX_PAGE = 100_000
# Ids beyond SQLite's 64-bit range would 500; nothing real is that big.


def _count(db: Session, *where) -> int:
    return db.scalar(select(func.count()).select_from(CatchPin).where(*where)) or 0


@router.get("/stats", response_model=StatsOut)
def stats(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> StatsOut:
    week = utcnow() - timedelta(days=7)
    users = lambda *w: db.scalar(select(func.count()).select_from(User).where(*w)) or 0  # noqa: E731
    return StatsOut(
        users=users(),
        users_new_7d=users(User.created_at >= week),
        users_active_7d=users(User.last_login_at >= week),
        admins=users(User.role == ROLE_ADMIN),
        suspended=users(User.status == USER_SUSPENDED),
        pins=_count(db),
        pins_new_7d=_count(db, CatchPin.created_at >= week),
        pins_public=_count(db, CatchPin.visibility == VISIBILITY_PUBLIC, CatchPin.status == PIN_PUBLISHED),
        pins_private=_count(db, CatchPin.visibility == VISIBILITY_PRIVATE),
        pins_hidden=_count(db, CatchPin.status == PIN_HIDDEN),
        pins_removed=_count(db, CatchPin.status == PIN_REMOVED),
        photos=db.scalar(select(func.count()).select_from(PinPhoto)) or 0,
        open_reports=db.scalar(select(func.count()).select_from(PinReport).where(PinReport.status == REPORT_OPEN)) or 0,
        pins_awaiting_review=db.scalar(
            select(func.count(func.distinct(PinReport.pin_id))).where(PinReport.status == REPORT_OPEN)
        )
        or 0,
        lake_reports_open=db.scalar(
            select(func.count()).select_from(LakeReport).where(LakeReport.status == REPORT_OPEN)
        )
        or 0,
        feedback_new=db.scalar(select(func.count()).select_from(Feedback).where(Feedback.status == FEEDBACK_NEW)) or 0,
        ai_spent_usd=round(ai_budget.spent(db), 4),
        ai_budget_usd=ai_budget.budget(),
    )


# ------------------------------------------------------------ lake reports


@router.get("/lake-reports", response_model=list[AdminLakeReportOut])
def lake_report_queue(
    status: str = Query(default=REPORT_OPEN, pattern=r"^(open|resolved)$"),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AdminLakeReportOut]:
    """Open lake reports, oldest first (the queue); resolved, newest first."""
    order = LakeReport.created_at.asc() if status == REPORT_OPEN else LakeReport.resolved_at.desc()
    rows = db.scalars(select(LakeReport).where(LakeReport.status == status).order_by(order).limit(200)).all()
    lakes = {
        w.id: w
        for w in db.scalars(select(Waterbody).where(Waterbody.id.in_({r.waterbody_id for r in rows if r.waterbody_id})))
    }
    reporters = {
        u.id: u.display_name
        for u in db.scalars(select(User).where(User.id.in_({r.reporter_id for r in rows if r.reporter_id})))
    }
    out = []
    for r in rows:
        lake = lakes.get(r.waterbody_id) if r.waterbody_id else None
        out.append(
            AdminLakeReportOut(
                id=r.id,
                reason=r.reason,
                reason_label=lake_report_service.reason_label(r.reason),
                waterbody_id=r.waterbody_id,
                lake_name=lake.name if lake else r.name,
                latitude=lake.latitude if lake else r.latitude,
                longitude=lake.longitude if lake else r.longitude,
                state_code=r.state_code,
                detail=r.detail,
                reporter=reporters.get(r.reporter_id) if r.reporter_id else None,
                status=r.status,
                resolution=r.resolution,
                created_at=r.created_at,
                resolved_at=r.resolved_at,
            )
        )
    return out


@router.post("/lake-reports/{report_id}/resolve", status_code=204, response_class=Response)
def resolve_lake_report(
    payload: LakeReportResolveIn,
    report_id: DbId,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    """Fixed (the data was corrected by hand) or dismissed. Recorded in the
    audit log either way."""
    report = db.get(LakeReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="No such report.")
    try:
        lake_report_service.resolve(report, admin, payload.resolution)
    except LakeReportError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
    audit.record(
        db, admin, f"lake_report.{payload.resolution}", "lake_report", report.id,
        reason=report.reason, waterbody_id=report.waterbody_id, name=report.name, note=payload.note,
    )
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------- reports


@router.get("/reports", response_model=list[ReportGroupOut])
def report_queue(admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[ReportGroupOut]:
    """Open reports grouped by pin, pins with the most reports first."""
    reports = db.scalars(
        select(PinReport)
        .where(PinReport.status == REPORT_OPEN)
        .options(selectinload(PinReport.reporter), selectinload(PinReport.pin).selectinload(CatchPin.photos))
        .order_by(PinReport.created_at)
    ).all()
    groups: dict[int, list[PinReport]] = {}
    for r in reports:
        groups.setdefault(r.pin_id, []).append(r)
    pins = {p.id: p for p in (reports_[0].pin for reports_ in groups.values())}
    lakes = waters_for(db, list(pins.values()))
    ordered = sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[1][0].created_at))
    return [
        ReportGroupOut(
            pin=PinSummaryOut(**summary_fields(pins[pin_id], admin, lakes)),
            reports=[
                ReportItemOut(
                    id=r.id,
                    reason=r.reason,
                    reason_label=pin_service.REPORT_REASONS.get(r.reason, r.reason),
                    detail=r.detail,
                    reporter=r.reporter.display_name if r.reporter else "Deleted account",
                    created_at=r.created_at,
                )
                for r in items
            ],
        )
        for pin_id, items in ordered
    ]


@router.post("/reports/{pin_id}/resolve", response_model=AdminPinOut)
def resolve_reports(
    payload: ResolveIn,
    pin_id: DbId,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminPinOut:
    pin = db.get(CatchPin, pin_id)
    if pin is None:
        raise HTTPException(status_code=404, detail="No such pin.")
    outcome = {"dismiss": "dismissed", "hide": "hidden", "remove": "removed"}.get(payload.action)
    if outcome is None:
        raise HTTPException(status_code=422, detail="action is dismiss, hide or remove")
    open_reports = [r for r in pin.reports if r.status == REPORT_OPEN]
    if not open_reports:
        raise HTTPException(status_code=409, detail="This pin has no open reports.")
    now = utcnow()
    for r in open_reports:
        r.status, r.resolution, r.resolved_at, r.resolved_by_id = REPORT_RESOLVED, outcome, now, admin.id
    before = pin.status
    if payload.action == "dismiss":
        # Reports dismissed: a pin the reports had auto-hidden comes back.
        if pin.status == PIN_HIDDEN and pin.status_reason == "reports":
            pin.status, pin.status_reason = PIN_PUBLISHED, None
    elif payload.action == "hide":
        pin.status, pin.status_reason = PIN_HIDDEN, "moderator"
    else:
        pin.status, pin.status_reason = PIN_REMOVED, "moderator"
    audit.record(
        db, admin, f"reports.{outcome}", "pin", pin.id,
        reports=len(open_reports), status_before=before, status_after=pin.status, note=payload.note,
    )
    db.commit()
    return _admin_pin(db, pin, admin)


@router.get("/comment-reports", response_model=list[CommentReportGroupOut])
def comment_report_queue(admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[CommentReportGroupOut]:
    """Comments with open reports, the most reported first."""
    reports = db.scalars(
        select(CommentReport)
        .where(CommentReport.status == REPORT_OPEN)
        .options(selectinload(CommentReport.comment).selectinload(PinComment.user), selectinload(CommentReport.comment).selectinload(PinComment.pin))
        .order_by(CommentReport.created_at)
    ).all()
    reporters = {u.id: u.display_name for u in db.scalars(select(User).where(User.id.in_({r.reporter_id for r in reports if r.reporter_id})))}
    groups: dict[int, list[CommentReport]] = {}
    for r in reports:
        groups.setdefault(r.comment_id, []).append(r)
    return [
        CommentReportGroupOut(
            comment=ReportedCommentOut(
                id=c.id,
                body=c.body,
                status=c.status,
                author=c.user.display_name,
                pin_id=c.pin_id,
                pin_title=c.pin.title,
                created_at=c.created_at,
            ),
            reports=[
                CommentReportItemOut(
                    id=r.id,
                    reason=r.reason,
                    reason_label=pin_service.REPORT_REASONS.get(r.reason, r.reason),
                    reporter=reporters.get(r.reporter_id or 0, "Deleted account"),
                    created_at=r.created_at,
                )
                for r in items
            ],
        )
        for items in sorted(groups.values(), key=lambda g: (-len(g), g[0].created_at))
        for c in [items[0].comment]
    ]


@router.post("/comment-reports/{comment_id}/resolve", response_model=CommentResolvedOut)
def resolve_comment_reports(
    payload: ResolveIn, comment_id: DbId, admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> CommentResolvedOut:
    comment = db.get(PinComment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="No such comment.")
    outcome = {"dismiss": "dismissed", "remove": "removed"}.get(payload.action)
    if outcome is None:
        raise HTTPException(status_code=422, detail="action is dismiss or remove")
    open_reports = [r for r in comment.reports if r.status == REPORT_OPEN]
    if not open_reports:
        raise HTTPException(status_code=409, detail="This comment has no open reports.")
    audit.record(db, admin, f"comment_reports.{outcome}", "comment", comment.id, reports=len(open_reports), note=payload.note)
    if payload.action == "remove":
        db.delete(comment)
    else:
        now = utcnow()
        for r in open_reports:
            r.status, r.resolution, r.resolved_at, r.resolved_by_id = REPORT_RESOLVED, outcome, now, admin.id
        comment.status = PIN_PUBLISHED
    db.commit()
    return CommentResolvedOut(id=comment_id, outcome=outcome)


# ------------------------------------------------------------------- pins


def _admin_pin(db: Session, pin: CatchPin, admin: User, lakes=None) -> AdminPinOut:
    lakes = lakes if lakes is not None else waters_for(db, [pin])
    return AdminPinOut(
        **summary_fields(pin, admin, lakes),
        open_reports=pin_service.open_report_count(db, pin.id),
        author_email=pin.user.email,
    )


@router.get("/pins", response_model=AdminPinPage)
def admin_pins(
    status: str | None = None,
    visibility: str | None = None,
    state: str | None = Query(default=None, pattern=r"^[A-Za-z]{2}$"),
    q: str | None = Query(default=None, max_length=80),
    page: int = Query(default=1, ge=1, le=MAX_PAGE),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminPinPage:
    where = []
    if state:
        where.append(CatchPin.state_code == state.upper())
    if status:
        where.append(CatchPin.status == status)
    if visibility:
        where.append(CatchPin.visibility == visibility)
    if q:
        text = q.strip().lower()
        where.append(or_(*(func.lower(c).contains(text, autoescape=True) for c in (CatchPin.title, User.display_name, User.email))))
    base = select(CatchPin).join(User, User.id == CatchPin.user_id).where(*where)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    pins = db.scalars(
        base.options(selectinload(CatchPin.photos), selectinload(CatchPin.user))
        .order_by(CatchPin.created_at.desc(), CatchPin.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()
    lakes = waters_for(db, list(pins))
    return AdminPinPage(
        total=total, page=page, page_size=PAGE_SIZE, items=[_admin_pin(db, p, admin, lakes) for p in pins]
    )


@router.post("/pins/{pin_id}/status", response_model=AdminPinOut)
def set_pin_status(
    payload: PinStatusIn,
    pin_id: DbId,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminPinOut:
    pin = db.get(CatchPin, pin_id)
    if pin is None:
        raise HTTPException(status_code=404, detail="No such pin.")
    if payload.status not in (PIN_PUBLISHED, PIN_HIDDEN, PIN_REMOVED):
        raise HTTPException(status_code=422, detail="status is published, hidden or removed")
    before = pin.status
    pin.status = payload.status
    pin.status_reason = None if payload.status == PIN_PUBLISHED else "moderator"
    audit.record(db, admin, f"pin.{payload.status}", "pin", pin.id, status_before=before, note=payload.note)
    db.commit()
    return _admin_pin(db, pin, admin)


@router.delete("/pins/{pin_id}", status_code=204, response_class=Response)
def purge_pin(
    pin_id: DbId,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    """Deletes the pin and its photo files for good — for content that must
    not be kept at all. Everyday moderation should use `removed`, which is
    reversible."""
    pin = db.get(CatchPin, pin_id)
    if pin is None:
        raise HTTPException(status_code=404, detail="No such pin.")
    audit.record(db, admin, "pin.purged", "pin", pin.id, title=pin.title, author_id=pin.user_id)
    pin_service.delete_pin(db, pin, get_store())
    db.commit()
    return Response(status_code=204)


# ------------------------------------------------------------------ users


def _user_out(db: Session, u: User) -> AdminUserOut:
    pins = db.scalar(select(func.count()).select_from(CatchPin).where(CatchPin.user_id == u.id)) or 0
    against = db.scalar(
        select(func.count(PinReport.id)).join(CatchPin, CatchPin.id == PinReport.pin_id).where(CatchPin.user_id == u.id)
    ) or 0
    return AdminUserOut(
        id=u.id,
        email=u.email,
        display_name=u.display_name,
        role=u.role,
        status=u.status,
        has_password=u.password_hash is not None,
        google_connected=u.google_sub is not None,
        created_at=u.created_at,
        last_login_at=u.last_login_at,
        email_verified=u.email_verified_at is not None or u.google_sub is not None,
        pins=pins,
        reports_against=against,
    )


USER_SORTS = ("newest", "last_seen", "catches", "reports")


def _user_counts(db: Session) -> UserCountsOut:
    n = lambda *w: db.scalar(select(func.count()).select_from(User).where(*w)) or 0  # noqa: E731
    return UserCountsOut(
        all=n(),
        admins=n(User.role == ROLE_ADMIN),
        suspended=n(User.status == USER_SUSPENDED),
        unconfirmed=n(User.email_verified_at.is_(None), User.google_sub.is_(None)),
        new_7d=n(User.created_at >= utcnow() - timedelta(days=7)),
    )


@router.get("/users", response_model=AdminUserPage)
def admin_users(
    q: str | None = Query(default=None, max_length=80),
    role: str | None = None,
    status: str | None = None,
    unconfirmed: bool = False,
    sort: str = "newest",
    page: int = Query(default=1, ge=1, le=MAX_PAGE),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserPage:
    if sort not in USER_SORTS:
        raise HTTPException(status_code=422, detail="Sort by newest, last_seen, catches or reports.")
    where = []
    if q:
        text = q.strip().lower()
        match = [func.lower(User.email).contains(text, autoescape=True), func.lower(User.display_name).contains(text, autoescape=True)]
        # "#12" or "12": what the feedback and audit tabs call an account.
        if text.lstrip("#").isdigit() and len(text) < 12:
            match.append(User.id == int(text.lstrip("#")))
        where.append(or_(*match))
    if role:
        where.append(User.role == role)
    if status:
        where.append(User.status == status)
    if unconfirmed:
        where.append(User.email_verified_at.is_(None))
        where.append(User.google_sub.is_(None))
    total = db.scalar(select(func.count()).select_from(User).where(*where)) or 0
    if sort == "last_seen":
        order = (case((User.last_login_at.is_(None), 1), else_=0), User.last_login_at.desc(), User.id.desc())
    elif sort == "catches":
        n_pins = select(func.count(CatchPin.id)).where(CatchPin.user_id == User.id).scalar_subquery()
        order = (n_pins.desc(), User.id.desc())
    elif sort == "reports":
        n_reports = (
            select(func.count(PinReport.id))
            .join(CatchPin, CatchPin.id == PinReport.pin_id)
            .where(CatchPin.user_id == User.id)
            .scalar_subquery()
        )
        order = (n_reports.desc(), User.id.desc())
    else:
        order = (User.created_at.desc(), User.id.desc())
    users = db.scalars(select(User).where(*where).order_by(*order).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)).all()
    return AdminUserPage(
        total=total, page=page, page_size=PAGE_SIZE, items=[_user_out(db, u) for u in users], counts=_user_counts(db)
    )


def _target(db: Session, user_id: int) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="No such user.")
    return target


def _user_detail(db: Session, u: User) -> AdminUserDetailOut:
    n_pins = lambda *w: db.scalar(select(func.count()).select_from(CatchPin).where(CatchPin.user_id == u.id, *w)) or 0  # noqa: E731
    now = utcnow()
    live = (UserSession.user_id == u.id, UserSession.revoked_at.is_(None), UserSession.expires_at > now)
    recent = db.scalars(
        select(CatchPin).where(CatchPin.user_id == u.id).order_by(CatchPin.created_at.desc(), CatchPin.id.desc()).limit(5)
    ).all()
    history = db.scalars(
        select(AuditLog)
        .where(AuditLog.target_type == "user", AuditLog.target_id == u.id)
        .order_by(AuditLog.id.desc())
        .limit(8)
    ).all()
    return AdminUserDetailOut(
        **_user_out(db, u).model_dump(),
        last_seen_at=db.scalar(select(func.max(UserSession.last_seen_at)).where(UserSession.user_id == u.id)),
        sessions=db.scalar(select(func.count()).select_from(UserSession).where(*live)) or 0,
        pins_public=n_pins(CatchPin.visibility == VISIBILITY_PUBLIC, CatchPin.status == PIN_PUBLISHED),
        pins_private=n_pins(CatchPin.visibility == VISIBILITY_PRIVATE),
        pins_hidden=n_pins(CatchPin.status.in_((PIN_HIDDEN, PIN_REMOVED))),
        reports_filed=db.scalar(select(func.count()).select_from(PinReport).where(PinReport.reporter_id == u.id)) or 0,
        feedback=db.scalar(select(func.count()).select_from(Feedback).where(Feedback.user_id == u.id)) or 0,
        recent_pins=[
            AdminUserCatchOut(id=p.id, title=p.title, status=p.status, visibility=p.visibility, created_at=p.created_at)
            for p in recent
        ],
        history=[_audit_out(e) for e in history],
    )


@router.get("/users/{user_id}", response_model=AdminUserDetailOut)
def admin_user(user_id: DbId, _: User = Depends(require_admin), db: Session = Depends(get_db)) -> AdminUserDetailOut:
    return _user_detail(db, _target(db, user_id))


@router.post("/users/{user_id}/confirm-email", response_model=AdminUserDetailOut)
def admin_confirm_email(
    user_id: DbId, admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> AdminUserDetailOut:
    """For someone whose confirmation mail never came, once you know it's them."""
    target = _target(db, user_id)
    if target.email_verified_at is None:
        target.email_verified_at = utcnow()
        audit.record(db, admin, "user.email_confirmed", "user", target.id)
        db.commit()
    return _user_detail(db, target)


@router.post("/users/{user_id}/sign-out", response_model=AdminUserDetailOut)
def admin_sign_out(
    user_id: DbId, admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> AdminUserDetailOut:
    target = _target(db, user_id)
    if target.id == admin.id:
        raise HTTPException(status_code=409, detail="Sign yourself out from the account menu.")
    ended = auth_service.revoke_all_sessions(db, target)
    audit.record(db, admin, "user.signed_out", "user", target.id, sessions=ended)
    db.commit()
    return _user_detail(db, target)


@router.post("/users/{user_id}/reset-link", response_model=ResetLinkOut)
def admin_reset_link(
    payload: ResetLinkIn, user_id: DbId, admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> ResetLinkOut:
    """A password link for someone locked out: shown here once, to pass on,
    and emailed too if asked and the server can. Whoever holds it can take the
    account, so not for yourself or another admin, and it's in the audit log."""
    target = _target(db, user_id)
    if target.id == admin.id or target.is_admin:
        raise HTTPException(status_code=409, detail="Admins change their own password from the account page.")
    if not target.is_active:
        raise HTTPException(status_code=409, detail="Reactivate the account first.")
    emailed = payload.email_it and password_reset.can_email()
    link, expires = password_reset.issue(db, target, password_reset.HANDED_OVER_HOURS)
    audit.record(db, admin, "user.reset_link", "user", target.id, emailed=emailed)
    db.commit()
    if emailed:
        password_reset.deliver(password_reset.mail_for(target, link, password_reset.HANDED_OVER_HOURS))
    return ResetLinkOut(link=link, expires_at=expires, emailed=emailed)


@router.delete("/users/{user_id}", status_code=204, response_class=Response)
def admin_delete_user(
    user_id: DbId, admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> Response:
    """The account, its catches and their photos, for good."""
    target = _target(db, user_id)
    if target.id == admin.id:
        raise HTTPException(status_code=409, detail="Delete your own account from the account page.")
    if target.is_admin:
        raise HTTPException(status_code=409, detail="Remove their admin role first.")
    keys = pin_service.photo_keys_of(target)
    # Their name and address stay in the log, as when someone deletes themselves.
    audit.record(db, admin, "user.deleted_by_admin", "user", target.id, email=target.email, name=target.display_name, pins=len(target.pins))
    db.delete(target)
    db.commit()
    store = get_store()
    for key in keys:
        store.delete(key)
    return Response(status_code=204)


# --------------------------------------------------------------- feedback


def _feedback_out(r: Feedback) -> AdminFeedbackOut:
    return AdminFeedbackOut(
        id=r.id,
        message=r.message,
        page=r.page,
        lang=r.lang,
        status=r.status,
        created_at=r.created_at,
        handled_at=r.handled_at,
        user_id=r.user_id,
        author_name=r.user.display_name if r.user else None,
        author_email=r.user.email if r.user else None,
        signed_out=bool(r.signed_out),
        contact=r.contact,
    )


@router.get("/feedback", response_model=AdminFeedbackPage)
def admin_feedback(
    status: str | None = None,
    q: str | None = Query(default=None, max_length=80),
    page: int = Query(default=1, ge=1, le=MAX_PAGE),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminFeedbackPage:
    where = []
    if status:
        where.append(Feedback.status == status)
    if q:
        where.append(func.lower(Feedback.message).contains(q.strip().lower(), autoescape=True))
    total = db.scalar(select(func.count()).select_from(Feedback).where(*where)) or 0
    rows = db.scalars(
        select(Feedback)
        .where(*where)
        .options(selectinload(Feedback.user))
        .order_by(Feedback.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()
    return AdminFeedbackPage(total=total, page=page, page_size=PAGE_SIZE, items=[_feedback_out(r) for r in rows])


@router.get("/feedback/export", response_model=FeedbackExportOut)
def admin_feedback_export(
    status: str | None = None, _: User = Depends(require_admin), db: Session = Depends(get_db)
) -> FeedbackExportOut:
    """As text to pass on, or to paste to Claude: no names or addresses."""
    stmt = select(Feedback).order_by(Feedback.id.desc()).limit(500)
    if status:
        stmt = stmt.where(Feedback.status == status)
    rows = list(db.scalars(stmt).all())
    return FeedbackExportOut(count=len(rows), text=feedback_service.as_text(rows))


@router.post("/feedback/{feedback_id}", response_model=AdminFeedbackOut)
def admin_feedback_update(
    payload: FeedbackUpdateIn, feedback_id: DbId, admin: User = Depends(require_admin), db: Session = Depends(get_db)
) -> AdminFeedbackOut:
    row = db.get(Feedback, feedback_id)
    if row is None:
        raise HTTPException(status_code=404, detail="No such message.")
    if payload.status not in feedback_service.STATUSES:
        raise HTTPException(status_code=422, detail="status is new or done")
    if row.status != payload.status:
        row.status = payload.status
        row.handled_at = utcnow() if payload.status != FEEDBACK_NEW else None
        audit.record(db, admin, f"feedback.{payload.status}", "feedback", row.id)
        db.commit()
    return _feedback_out(row)


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    payload: UserUpdateIn,
    user_id: DbId,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserOut:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="No such user.")
    if payload.role is None and payload.status is None and payload.display_name is None:
        raise HTTPException(status_code=422, detail="Nothing to change.")
    if payload.role not in (None, ROLE_USER, ROLE_ADMIN):
        raise HTTPException(status_code=422, detail="role is user or admin")
    if payload.status not in (None, USER_ACTIVE, USER_SUSPENDED):
        raise HTTPException(status_code=422, detail="status is active or suspended")
    if target.id == admin.id and (payload.role is not None or payload.status is not None):
        raise HTTPException(status_code=409, detail="You can't change your own role or status.")
    if payload.display_name is not None:
        try:
            name = auth_service.clean_display_name(payload.display_name)
        except AuthError as exc:
            raise HTTPException(status_code=exc.status, detail=exc.message) from exc
    losing_admin = target.is_admin and target.is_active and (
        payload.role == ROLE_USER or payload.status == USER_SUSPENDED
    )
    if losing_admin and auth_service.active_admin_count(db) <= 1:
        raise HTTPException(status_code=409, detail="That would leave the site with no active admin.")

    changes: dict[str, str] = {}
    if payload.display_name is not None and name != target.display_name:
        changes["display_name"] = f"{target.display_name} -> {name}"
        target.display_name = name
    if payload.role is not None and payload.role != target.role:
        changes["role"] = f"{target.role} -> {payload.role}"
        target.role = payload.role
    if payload.status is not None and payload.status != target.status:
        changes["status"] = f"{target.status} -> {payload.status}"
        target.status = payload.status
        if payload.status == USER_SUSPENDED:
            # Suspension takes effect now, not when their cookie expires.
            changes["sessions_revoked"] = str(auth_service.revoke_all_sessions(db, target))
    db.flush()
    # Re-checked after the change, inside the same transaction: two admins
    # demoting each other at the same moment must not both succeed.
    if auth_service.active_admin_count(db) == 0:
        db.rollback()
        raise HTTPException(status_code=409, detail="That would leave the site with no active admin.")
    if changes:
        audit.record(db, admin, "user.updated", "user", target.id, **changes)
    db.commit()
    return _user_out(db, target)


# ------------------------------------------------------------------ audit


def _audit_out(r: AuditLog) -> AuditOut:
    return AuditOut(
        id=r.id,
        actor=(
            r.actor.display_name
            if r.actor
            else (f"{r.actor_label} (deleted)" if r.actor_label else "System")
        ),
        action=r.action,
        target_type=r.target_type,
        target_id=r.target_id,
        detail=r.detail,
        created_at=r.created_at,
    )


@router.get("/audit", response_model=AuditPage)
def audit_log(
    page: int = Query(default=1, ge=1, le=MAX_PAGE),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AuditPage:
    total = db.scalar(select(func.count()).select_from(AuditLog)) or 0
    rows = db.scalars(
        select(AuditLog)
        .options(selectinload(AuditLog.actor))
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()
    return AuditPage(
        total=total,
        page=page,
        page_size=PAGE_SIZE,
        items=[_audit_out(r) for r in rows],
    )


# ------------------------------------------------------------- Ask misses


@router.get("/ask-misses", response_model=list[AskMissOut])
def ask_miss_list(
    days: int = Query(default=30, ge=1, le=ask_misses.RETENTION_DAYS),
    outcome: str | None = Query(default=None, pattern=r"^(no_match|unguided_fish|other_state|off_topic)$"),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AskMissOut]:
    """What Ask couldn't answer, most asked first: what to write next."""
    return [AskMissOut(**vars(r)) for r in ask_misses.top(db, days, outcome)]
