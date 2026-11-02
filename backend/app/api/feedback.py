"""/api/feedback — a message to FishEye from a signed-in account."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth_deps import require_user, same_origin
from app.api.deps import get_db
from app.core.security import RateLimiter
from app.models.community import User
from app.schemas.feedback import FeedbackIn, FeedbackSentOut
from app.services import feedback as feedback_service

router = APIRouter(prefix="/feedback", tags=["feedback"], dependencies=[Depends(same_origin)])

# Plenty for someone with a lot to say; not enough to fill the admin's queue.
by_user = RateLimiter(limit=10, window_seconds=24 * 60 * 60)


@router.post("", response_model=FeedbackSentOut, status_code=201)
def send_feedback(payload: FeedbackIn, user: User = Depends(require_user), db: Session = Depends(get_db)) -> FeedbackSentOut:
    key = str(user.id)
    if by_user.blocked_for(key) > 0:
        raise HTTPException(status_code=429, detail="You've sent a lot today. Thanks! Try again tomorrow.")
    try:
        row = feedback_service.create(db, user, payload.message, payload.page, payload.lang)
    except feedback_service.FeedbackError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    by_user.hit(key)
    db.commit()
    return FeedbackSentOut(id=row.id)
