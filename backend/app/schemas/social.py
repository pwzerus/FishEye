from datetime import datetime

from pydantic import BaseModel, Field


class LikeOut(BaseModel):
    liked: bool
    like_count: int


class CommentIn(BaseModel):
    body: str = Field(max_length=2000)


class CommentAuthorOut(BaseModel):
    id: int
    display_name: str


class CommentOut(BaseModel):
    id: int
    body: str
    created_at: datetime
    author: CommentAuthorOut
    status: str  # "published" | "hidden": a moderator sees both
    is_mine: bool
    can_delete: bool
    can_report: bool


class CommentReportIn(BaseModel):
    reason: str


class CommentReportOut(BaseModel):
    received: bool
    hidden: bool


class StandingOut(BaseModel):
    rank: int
    user_id: int
    display_name: str
    value: int
    is_me: bool


class LeaderboardOut(BaseModel):
    metric: str
    period: str
    entries: list[StandingOut]
    # Where the viewer stands, when signed in and on this board at all.
    me: StandingOut | None


class AnglerOut(BaseModel):
    id: int
    display_name: str
    joined_at: datetime
    catches: int
    confirmed: int
    likes: int


class AlertIn(BaseModel):
    species_slug: str
    latitude: float
    longitude: float
    place: str = Field(max_length=200)
    radius_miles: int
    lang: str | None = Field(default=None, max_length=8)


class AlertOut(BaseModel):
    id: int
    species_slug: str
    species_label: str
    place: str
    radius_miles: int
    created_at: datetime
    last_sent_at: datetime | None


class AlertsOut(BaseModel):
    alerts: list[AlertOut]
    email: str
    # Alerts go only to a confirmed address (services/alerts.py).
    email_confirmed: bool
    # Whether mail really leaves the server yet (MAIL_BACKEND=smtp).
    sending: bool
    max_alerts: int
    min_radius: int
    max_radius: int


class UnsubscribeIn(BaseModel):
    token: str = Field(max_length=200)


class UnsubscribeOut(BaseModel):
    species_label: str
    place: str
