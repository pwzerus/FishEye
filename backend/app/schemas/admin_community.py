from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.pins import PinSummaryOut


class StatsOut(BaseModel):
    users: int
    users_new_7d: int
    users_active_7d: int
    admins: int
    suspended: int
    pins: int
    pins_new_7d: int
    pins_public: int
    pins_private: int
    pins_hidden: int
    pins_removed: int
    photos: int
    open_reports: int
    pins_awaiting_review: int


class ReportItemOut(BaseModel):
    id: int
    reason: str
    reason_label: str
    detail: str | None
    reporter: str
    created_at: datetime


class ReportGroupOut(BaseModel):
    pin: PinSummaryOut
    reports: list[ReportItemOut]


class ResolveIn(BaseModel):
    action: str  # "dismiss" | "hide" | "remove"
    note: str | None = Field(default=None, max_length=500)


class PinStatusIn(BaseModel):
    status: str  # "published" | "hidden" | "removed"
    note: str | None = Field(default=None, max_length=500)


class AdminPinOut(PinSummaryOut):
    open_reports: int
    author_email: str


class AdminUserOut(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    status: str
    has_password: bool
    google_connected: bool
    created_at: datetime
    last_login_at: datetime | None
    pins: int
    reports_against: int


class UserUpdateIn(BaseModel):
    role: str | None = None  # "user" | "admin"
    status: str | None = None  # "active" | "suspended"


class AuditOut(BaseModel):
    id: int
    actor: str  # display name, or "System"
    action: str
    target_type: str
    target_id: int
    detail: str | None
    created_at: datetime


class Page(BaseModel):
    total: int
    page: int
    page_size: int


class AdminPinPage(Page):
    items: list[AdminPinOut]


class AdminUserPage(Page):
    items: list[AdminUserOut]


class AuditPage(Page):
    items: list[AuditOut]
