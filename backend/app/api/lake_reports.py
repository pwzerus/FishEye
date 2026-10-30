"""/api/lake-reports — "something's wrong with this lake" and "a lake is
missing" (services/lake_reports.py, ADR 0039). Anyone may send one, a few
an hour per address; the admin side is in api/admin_community.py."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.auth_deps import optional_user, same_origin
from app.api.deps import get_db
from app.api.rate_limits import client_ip
from app.core.security import RateLimiter
from app.models.community import User
from app.schemas.lake_reports import LakeReportIn, LakeReportOptionsOut, LakeReportReceivedOut
from app.services import lake_reports as svc
from app.services.lake_reports import LakeReportError

router = APIRouter(prefix="/lake-reports", tags=["lake-reports"], dependencies=[Depends(same_origin)])

# Reports come from people without accounts too; this keeps one address
# from filling the admin's queue. The address itself is never stored.
report_by_ip = RateLimiter(limit=10, window_seconds=60 * 60)


@router.get("/options", response_model=LakeReportOptionsOut)
def options() -> LakeReportOptionsOut:
    return LakeReportOptionsOut(reasons=[{"id": k, "label": v} for k, v in svc.REASONS.items()])


@router.post("", response_model=LakeReportReceivedOut, status_code=201)
def create(
    payload: LakeReportIn,
    request: Request,
    user: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
) -> LakeReportReceivedOut:
    ip = client_ip(request)
    wait = report_by_ip.blocked_for(ip)
    if wait > 0:
        raise HTTPException(
            status_code=429,
            detail="You've sent a lot of reports. Try again later.",
            headers={"Retry-After": str(int(wait) + 1)},
        )
    try:
        report = svc.create(
            db, user, reason=payload.reason, waterbody_id=payload.waterbody_id, name=payload.name,
            latitude=payload.latitude, longitude=payload.longitude, detail=payload.detail,
        )
    except LakeReportError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
    report_by_ip.hit(ip)
    db.commit()
    return LakeReportReceivedOut(received=True, id=report.id)
