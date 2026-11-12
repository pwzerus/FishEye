"""/api/feedback — a message to FishEye, from an account or signed out."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api import rate_limits
from app.api.auth_deps import optional_user, same_origin
from app.api.deps import get_db
from app.api.rate_limits import client_ip
from app.api.zh_hant import asked_in_traditional
from app.core.config import get_settings
from app.core.security import RateLimiter
from app.knowledge.zh_hant import ZHT
from app.models.community import User
from app.schemas.feedback import FeedbackIn, FeedbackSentOut
from app.services import feedback as feedback_service

router = APIRouter(prefix="/feedback", tags=["feedback"], dependencies=[Depends(same_origin)])

DAY = 24 * 60 * 60
# Plenty for someone with a lot to say; not enough to fill the admin's queue.
by_user = RateLimiter(limit=10, window_seconds=DAY)
# Signed out there is no account to count, so the address is counted, and
# every signed-out message together has a daily ceiling: a script can fill
# at most that much of the queue in a day.
by_ip = RateLimiter(limit=5, window_seconds=DAY)
signed_out_everyone = RateLimiter(limit=100, window_seconds=DAY)

TOO_MANY = "You've sent a lot today. Thanks! Try again tomorrow."
FULL = "We've had a lot of messages today. Please try again tomorrow, or sign in to send one now."


def _limits(user: User | None, request: Request) -> list[tuple[RateLimiter, str, str]]:
    if user is not None:
        return [(by_user, str(user.id), TOO_MANY)]
    if not get_settings().rate_limits_enabled:
        return []
    return [(by_ip, client_ip(request), TOO_MANY), (signed_out_everyone, rate_limits.EVERYONE, FULL)]


@router.post("", response_model=FeedbackSentOut, status_code=201)
def send_feedback(
    payload: FeedbackIn,
    request: Request,
    user: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
) -> FeedbackSentOut:
    limits = _limits(user, request)
    for limiter, key, message in limits:
        if limiter.blocked_for(key) > 0:
            raise HTTPException(status_code=429, detail=message)
    try:
        # 繁體中文 arrives as zh (api/zh_hant.py); the admin page should say zht.
        lang = ZHT if asked_in_traditional(request) else payload.lang
        row = feedback_service.create(db, user, payload.message, payload.page, lang, payload.contact)
    except feedback_service.FeedbackError as exc:
        raise HTTPException(status_code=422, detail=exc.message) from exc
    for limiter, key, _message in limits:
        limiter.hit(key)
    db.commit()
    return FeedbackSentOut(id=row.id)
