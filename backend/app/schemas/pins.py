from datetime import date, datetime

from pydantic import BaseModel, Field


class PinAuthorOut(BaseModel):
    id: int
    display_name: str


class PinLakeOut(BaseModel):
    id: int
    name: str


class PinPhotoOut(BaseModel):
    id: int
    url: str
    thumb_url: str
    width: int
    height: int


class PinSummaryOut(BaseModel):
    id: int
    latitude: float
    longitude: float
    title: str
    species_slug: str | None
    species_label: str | None
    caught_on: date | None
    created_at: datetime
    visibility: str  # "public" | "private"
    status: str  # "published" | "hidden" | "removed"
    status_reason: str | None
    author: PinAuthorOut
    lake: PinLakeOut | None
    photo_count: int
    thumb_url: str | None
    is_mine: bool


class PinDetailOut(PinSummaryOut):
    note: str | None
    photos: list[PinPhotoOut]
    can_edit: bool
    can_report: bool
    reported_by_me: bool


class PinUpdateIn(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=2000)
    species_slug: str | None = None
    species_other: str | None = Field(default=None, max_length=120)
    caught_on: date | None = None
    visibility: str | None = None
    # Explicit clears, since None means "unchanged" for the fields above.
    clear_note: bool = False
    clear_species: bool = False
    clear_caught_on: bool = False


class ReportIn(BaseModel):
    reason: str
    detail: str | None = Field(default=None, max_length=1000)


class ReportOut(BaseModel):
    received: bool
    pin_hidden: bool


class PinOptionsOut(BaseModel):
    species: list[dict[str, str]]  # [{slug, label}]
    report_reasons: list[dict[str, str]]  # [{id, label}]
    max_photos: int
    max_photo_mb: int
