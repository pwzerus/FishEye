from datetime import datetime

from pydantic import BaseModel

from app.services.tpwd_refresh_job import JobStatus


class RefreshTriggerOut(BaseModel):
    status: JobStatus
    message: str


class LakeResultOut(BaseModel):
    name: str
    status: str
    species_written: int
    detail: str


class RefreshStatusOut(BaseModel):
    status: JobStatus
    started_at: datetime | None
    finished_at: datetime | None
    total_written: int | None
    dry_run: bool | None
    lake_results: list[LakeResultOut] | None
    error: str | None
