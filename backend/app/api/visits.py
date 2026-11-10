"""/api/visits — the visit counter (services/visits.py), and its numbers
for admins."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import rate_limits
from app.api.auth_deps import require_admin, same_origin
from app.api.deps import get_db
from app.core.security import RateLimiter
from app.models.community import User
from app.services import visits as svc

router = APIRouter(prefix="/visits", tags=["visits"], dependencies=[Depends(same_origin)])

# Kept in memory and forgotten, like every limit here: it stops one client
# from inflating the counts, and the address is never stored.
VISITS = rate_limits.Budget("visits", per_client=[RateLimiter(60, rate_limits.MINUTE)])


class VisitIn(BaseModel):
    path: str = Field(max_length=500)
    referrer: str | None = Field(default=None, max_length=500)
    ref: str | None = Field(default=None, max_length=80)


class CountOut(BaseModel):
    key: str
    count: int


class VisitSummaryOut(BaseModel):
    days: int
    total: int
    by_day: list[CountOut]
    by_page: list[CountOut]
    by_source: list[CountOut]
    # The same numbers as text, to read or to paste to someone.
    text: str


@router.post("", status_code=204, dependencies=[Depends(VISITS)])
def count_visit(payload: VisitIn, request: Request, db: Session = Depends(get_db)) -> Response:
    """204 whether it was counted or not: the page has nothing to do either way."""
    own_host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    if svc.record(db, payload.path, payload.referrer, payload.ref, own_host.split(":")[0]):
        db.commit()
    return Response(status_code=204)


@router.get("/summary", response_model=VisitSummaryOut)
def visit_summary(
    days: int = Query(default=30, ge=1, le=365),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> VisitSummaryOut:
    s = svc.summary(db, days)
    return VisitSummaryOut(
        days=s.days,
        total=s.total,
        by_day=[CountOut(key=d.isoformat(), count=n) for d, n in s.by_day],
        by_page=[CountOut(key=p, count=n) for p, n in s.by_page],
        by_source=[CountOut(key=src, count=n) for src, n in s.by_source],
        text=svc.as_text(s),
    )
