"""In-memory job-status tracker for the TPWD manual-refresh admin endpoint.

Deliberately not a real task queue (Celery/RQ/etc.) — this is a portfolio
demo with a single-process backend and one admin operator, not a
multi-worker production system. An in-memory singleton is the honest,
simplest thing that actually matches the deployment shape; swap it for a
real queue if this backend is ever run with more than one worker process
(the module docstring says so precisely because that's a real limitation
worth being upfront about, not a thing to quietly outgrow).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from app.data_import.tpwd_lake_survey_scraper import IngestSummary, run as run_scraper


class JobStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class RefreshJobState:
    status: JobStatus = JobStatus.IDLE
    started_at: datetime | None = None
    finished_at: datetime | None = None
    summary: IngestSummary | None = None
    error: str | None = None


class TpwdRefreshJob:
    """One job at a time, guarded by a lock — a second trigger while one
    is running is rejected by the API layer (see app/api/admin.py) rather
    than queued, so there's never ambiguity about which run produced
    which result."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = RefreshJobState()

    def reset(self) -> None:
        """Testing/ops escape hatch — not exposed via any API route."""
        with self._lock:
            self._state = RefreshJobState()

    def snapshot(self) -> RefreshJobState:
        with self._lock:
            return RefreshJobState(**vars(self._state))

    def try_start(self) -> bool:
        """Returns False (and does nothing) if a run is already in
        progress — the caller should report 409 Conflict."""
        with self._lock:
            if self._state.status == JobStatus.RUNNING:
                return False
            self._state = RefreshJobState(status=JobStatus.RUNNING, started_at=datetime.now(timezone.utc))
            return True

    def run_and_record(self, dry_run: bool = False) -> None:
        """Meant to be handed to FastAPI's BackgroundTasks — call
        try_start() first (synchronously, in the request handler) so a
        409 can be returned immediately; this method does the slow part."""
        try:
            summary = run_scraper(dry_run=dry_run)
            with self._lock:
                self._state.status = JobStatus.DONE
                self._state.finished_at = datetime.now(timezone.utc)
                self._state.summary = summary
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any failure
            # must flip status away from RUNNING, or the job looks stuck
            # forever and the admin button never lets the user retry.
            with self._lock:
                self._state.status = JobStatus.ERROR
                self._state.finished_at = datetime.now(timezone.utc)
                self._state.error = f"{exc.__class__.__name__}: {exc}"


# Module-level singleton — intentional (see class docstring: one process,
# one admin operator, no shared state needed across requests beyond this).
tpwd_refresh_job = TpwdRefreshJob()
