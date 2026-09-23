"""Admin-only endpoints — currently just the TPWD manual-refresh trigger.

Gated by a single shared token (Settings.admin_api_token), not a real user
auth system. That's a deliberate, disclosed shortcut for a portfolio demo
with exactly one operator (me) — see docs/adr/0003-tpwd-manual-refresh.md
for the reasoning and what a real deployment would need instead (per-user
accounts, rate limiting, audit logging).
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException

from app.core.config import get_settings
from app.schemas.admin import LakeResultOut, RefreshStatusOut, RefreshTriggerOut
from app.services.tpwd_refresh_job import JobStatus, tpwd_refresh_job

router = APIRouter(prefix="/admin", tags=["admin"])


def _check_admin_token(x_admin_token: str | None) -> None:
    settings = get_settings()
    if not settings.admin_api_token:
        # Fail closed: an unconfigured token means the endpoint doesn't
        # exist as far as any caller is concerned, not "anyone can use
        # it." A missing secret should never widen access.
        raise HTTPException(status_code=503, detail="admin endpoints are not configured")
    if x_admin_token != settings.admin_api_token:
        raise HTTPException(status_code=401, detail="invalid or missing X-Admin-Token")


@router.post("/tpwd-refresh", response_model=RefreshTriggerOut, status_code=202)
def trigger_tpwd_refresh(
    background_tasks: BackgroundTasks,
    dry_run: bool = False,
    x_admin_token: str | None = Header(default=None),
) -> RefreshTriggerOut:
    _check_admin_token(x_admin_token)

    started = tpwd_refresh_job.try_start()
    if not started:
        raise HTTPException(status_code=409, detail="a refresh is already running")

    # Runs after this response is sent — the button gets an immediate
    # 202 instead of hanging for the ~15s the real scraper run takes
    # (7 lakes x 2s politeness delay), and the frontend polls status.
    background_tasks.add_task(tpwd_refresh_job.run_and_record, dry_run=dry_run)
    return RefreshTriggerOut(status=JobStatus.RUNNING, message="refresh started")


@router.get("/tpwd-refresh/status", response_model=RefreshStatusOut)
def get_tpwd_refresh_status(x_admin_token: str | None = Header(default=None)) -> RefreshStatusOut:
    _check_admin_token(x_admin_token)

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
