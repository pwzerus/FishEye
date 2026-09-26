"""Admin-only endpoints — the TPWD manual-refresh trigger.

Originally gated only by a shared token (Settings.admin_api_token), a
disclosed shortcut from before there were accounts (ADR 0003). Now a
signed-in admin (ADR 0016) may use it too; the token still works for
scripts and CI.
"""
from __future__ import annotations

import hmac

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException

from app.api.auth_deps import optional_user, same_origin
from app.models.community import User

from app.core.config import get_settings
from app.schemas.admin import LakeResultOut, RefreshStatusOut, RefreshTriggerOut
from app.services.tpwd_refresh_job import JobStatus, tpwd_refresh_job

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(same_origin)])


def _check_admin_token(x_admin_token: str | None, user: User | None = None) -> None:
    if user is not None and user.is_admin:
        return
    settings = get_settings()
    if not settings.admin_api_token:
        # Fail closed: an unconfigured token means the endpoint doesn't
        # exist as far as any caller is concerned, not "anyone can use
        # it." A missing secret should never widen access.
        raise HTTPException(status_code=503, detail="admin endpoints are not configured")
    if not x_admin_token or not hmac.compare_digest(
        x_admin_token.encode("utf-8"), settings.admin_api_token.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="invalid or missing X-Admin-Token")


@router.post("/tpwd-refresh", response_model=RefreshTriggerOut, status_code=202)
def trigger_tpwd_refresh(
    background_tasks: BackgroundTasks,
    dry_run: bool = False,
    x_admin_token: str | None = Header(default=None),
    user: User | None = Depends(optional_user),
) -> RefreshTriggerOut:
    _check_admin_token(x_admin_token, user)

    started = tpwd_refresh_job.try_start()
    if not started:
        raise HTTPException(status_code=409, detail="a refresh is already running")

    # Runs after this response is sent — the button gets an immediate
    # 202 instead of hanging for the ~15s the real scraper run takes
    # (7 lakes x 2s politeness delay), and the frontend polls status.
    background_tasks.add_task(tpwd_refresh_job.run_and_record, dry_run=dry_run)
    return RefreshTriggerOut(status=JobStatus.RUNNING, message="refresh started")


@router.get("/tpwd-refresh/status", response_model=RefreshStatusOut)
def get_tpwd_refresh_status(
    x_admin_token: str | None = Header(default=None),
    user: User | None = Depends(optional_user),
) -> RefreshStatusOut:
    _check_admin_token(x_admin_token, user)

    state = tpwd_refresh_job.snapshot()
    return RefreshStatusOut(
        status=state.status,
        started_at=state.started_at,
        finished_at=state.finished_at,
        total_written=state.summary.total_written if state.summary else None,
        total_access_points_written=(
            state.summary.total_access_points_written if state.summary else None
        ),
        dry_run=state.summary.dry_run if state.summary else None,
        lake_results=(
            [
                LakeResultOut(
                    name=r.name,
                    status=r.status,
                    species_written=r.species_written,
                    access_points_written=r.access_points_written,
                    detail=r.detail,
                )
                for r in state.summary.lake_results
            ]
            if state.summary
            else None
        ),
        error=state.error,
    )
