from datetime import datetime

from pydantic import BaseModel, Field


class LakeReportIn(BaseModel):
    # services/lake_reports.REASONS, or "missing".
    reason: str = Field(max_length=24)
    waterbody_id: int | None = Field(default=None, ge=1, le=2**62)
    # A missing lake: its name and where it is (the middle of the map).
    name: str | None = Field(default=None, max_length=200)
    latitude: float | None = None
    longitude: float | None = None
    detail: str | None = Field(default=None, max_length=2000)


class LakeReportReceivedOut(BaseModel):
    received: bool
    id: int


class LakeReportOptionsOut(BaseModel):
    reasons: list[dict[str, str]]  # [{id, label}]


class AdminLakeReportOut(BaseModel):
    id: int
    reason: str
    reason_label: str
    waterbody_id: int | None
    lake_name: str | None  # the reported lake's name, or the missing lake's
    latitude: float | None
    longitude: float | None
    state_code: str | None
    detail: str | None
    reporter: str | None  # display name; None for a report sent signed out
    status: str
    resolution: str | None
    created_at: datetime
    resolved_at: datetime | None


class LakeReportResolveIn(BaseModel):
    resolution: str  # "fixed" | "dismissed"
    note: str | None = Field(default=None, max_length=500)
