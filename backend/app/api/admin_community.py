"""/api/admin — community moderation and account management (admin role).

Every change here writes an audit entry in the same transaction. Guards
against locking the site out of its own admin: an admin can't demote or
suspend themselves, and the last active admin can't be demoted, suspended
or deleted.
"""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.auth_deps import require_admin, same_origin
from app.api.deps import get_db
from app.api.params import DbId
from app.api.pins import lakes_for, summary_fields
from app.db.types import utcnow
from app.models.community import (
    PIN_HIDDEN,
    PIN_PUBLISHED,
    PIN_REMOVED,
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
    PinPhoto,
    PinReport,
    User,
)
from app.schemas.admin_community import (
    AdminPinOut,
    AdminPinPage,
    AdminUserOut,
    AdminUserPage,
    AuditOut,
    AuditPage,
    PinStatusIn,
    ReportGroupOut,
    ReportItemOut,
    ResolveIn,
    StatsOut,
    UserUpdateIn,
)
from app.schemas.pins import PinSummaryOut
from app.services import audit
from app.services import auth as auth_service
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
    )


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
    lakes = lakes_for(db, list(pins.values()))
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


# ------------------------------------------------------------------- pins


def _admin_pin(db: Session, pin: CatchPin, admin: User, lakes=None) -> AdminPinOut:
    lakes = lakes if lakes is not None else lakes_for(db, [pin])
    return AdminPinOut(
        **summary_fields(pin, admin, lakes),
        open_reports=pin_service.open_report_count(db, pin.id),
        author_email=pin.user.email,
    )


@router.get("/pins", response_model=AdminPinPage)
def admin_pins(
    status: str | None = None,
    visibility: str | None = None,
    q: str | None = Query(default=None, max_length=80),
    page: int = Query(default=1, ge=1, le=MAX_PAGE),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminPinPage:
    where = []
    if status:
        where.append(CatchPin.status == status)
    if visibility:
        where.append(CatchPin.visibility == visibility)
    if q:
        like = f"%{q.strip().lower()}%"
        where.append(or_(func.lower(CatchPin.title).like(like), func.lower(User.display_name).like(like), func.lower(User.email).like(like)))
    base = select(CatchPin).join(User, User.id == CatchPin.user_id).where(*where)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    pins = db.scalars(
        base.options(selectinload(CatchPin.photos), selectinload(CatchPin.user))
        .order_by(CatchPin.created_at.desc(), CatchPin.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    ).all()
    lakes = lakes_for(db, list(pins))
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
        pins=pins,
        reports_against=against,
    )


@router.get("/users", response_model=AdminUserPage)
def admin_users(
    q: str | None = Query(default=None, max_length=80),
    role: str | None = None,
    status: str | None = None,
    page: int = Query(default=1, ge=1, le=MAX_PAGE),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminUserPage:
    where = []
    if q:
        like = f"%{q.strip().lower()}%"
        where.append(or_(func.lower(User.email).like(like), func.lower(User.display_name).like(like)))
    if role:
        where.append(User.role == role)
    if status:
        where.append(User.status == status)
    total = db.scalar(select(func.count()).select_from(User).where(*where)) or 0
    users = db.scalars(
        select(User).where(*where).order_by(User.created_at.desc(), User.id.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    ).all()
    return AdminUserPage(total=total, page=page, page_size=PAGE_SIZE, items=[_user_out(db, u) for u in users])


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
    if payload.role is None and payload.status is None:
        raise HTTPException(status_code=422, detail="Nothing to change.")
    if payload.role not in (None, ROLE_USER, ROLE_ADMIN):
        raise HTTPException(status_code=422, detail="role is user or admin")
    if payload.status not in (None, USER_ACTIVE, USER_SUSPENDED):
        raise HTTPException(status_code=422, detail="status is active or suspended")
    if target.id == admin.id:
        raise HTTPException(status_code=409, detail="You can't change your own role or status.")
    losing_admin = target.is_admin and target.is_active and (
        payload.role == ROLE_USER or payload.status == USER_SUSPENDED
    )
    if losing_admin and auth_service.active_admin_count(db) <= 1:
        raise HTTPException(status_code=409, detail="That would leave the site with no active admin.")

    changes: dict[str, str] = {}
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
        items=[
            AuditOut(
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
            for r in rows
        ],
    )
