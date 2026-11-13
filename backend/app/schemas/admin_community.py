from datetime import date, datetime

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
    # "Something's wrong with this lake" / "a lake is missing" (ADR 0039).
    lake_reports_open: int = 0
    feedback_new: int = 0
    # What the AI model has cost this month, estimated, and its ceiling.
    ai_spent_usd: float = 0.0
    ai_budget_usd: float = 0.0


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


class ReportedCommentOut(BaseModel):
    id: int
    body: str
    status: str
    author: str
    pin_id: int
    pin_title: str
    created_at: datetime


class CommentReportItemOut(BaseModel):
    id: int
    reason: str
    reason_label: str
    reporter: str
    created_at: datetime


class CommentReportGroupOut(BaseModel):
    comment: ReportedCommentOut
    reports: list[CommentReportItemOut]


class CommentResolvedOut(BaseModel):
    id: int
    outcome: str


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
    email_verified: bool = False
    pins: int
    reports_against: int
    plus_until: datetime | None = None  # FishEye Plus, if it hasn't run out


class UserUpdateIn(BaseModel):
    role: str | None = None  # "user" | "admin"
    status: str | None = None  # "active" | "suspended"
    display_name: str | None = Field(default=None, max_length=80)
    # FishEye Plus for this many days from now; 0 ends it. Until payments
    # are built, an admin gives it by hand.
    plus_days: int | None = Field(default=None, ge=0, le=3660)


class UserCountsOut(BaseModel):
    """For the filters above the list."""

    all: int
    admins: int
    suspended: int
    unconfirmed: int
    new_7d: int


class ResetLinkIn(BaseModel):
    email_it: bool = False


class ResetLinkOut(BaseModel):
    link: str
    expires_at: datetime
    emailed: bool


class AuditOut(BaseModel):
    id: int
    actor: str  # display name, or "System"
    action: str
    target_type: str
    target_id: int
    detail: str | None
    created_at: datetime


class AdminUserCatchOut(BaseModel):
    id: int
    title: str
    status: str
    visibility: str
    created_at: datetime


class AdminUserDetailOut(AdminUserOut):
    """One account, for acting on it with what's needed in front of you."""

    last_seen_at: datetime | None
    sessions: int
    pins_public: int
    pins_private: int
    pins_hidden: int
    reports_filed: int
    feedback: int
    recent_pins: list[AdminUserCatchOut]
    history: list[AuditOut]


class Page(BaseModel):
    total: int
    page: int
    page_size: int


class AdminPinPage(Page):
    items: list[AdminPinOut]


class AdminUserPage(Page):
    items: list[AdminUserOut]
    counts: UserCountsOut | None = None


class AuditPage(Page):
    items: list[AuditOut]


class AskMissOut(BaseModel):
    """A question Ask couldn't answer (services/ask_misses.py)."""

    question: str
    outcome: str
    lang: str
    state: str | None
    species_slug: str | None
    count: int  # times asked in the period
    days: int  # on how many days
    last_day: date
