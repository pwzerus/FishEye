from datetime import datetime

from pydantic import BaseModel, Field

from app.services.feedback import MAX_CHARS


class FeedbackIn(BaseModel):
    message: str = Field(max_length=MAX_CHARS)
    page: str | None = Field(default=None, max_length=500)
    lang: str | None = Field(default=None, max_length=8)
    # Signed out only: where to reply, if they want one.
    contact: str | None = Field(default=None, max_length=254)


class FeedbackSentOut(BaseModel):
    id: int


class AdminFeedbackOut(BaseModel):
    id: int
    message: str
    page: str | None
    lang: str | None
    status: str
    created_at: datetime
    handled_at: datetime | None
    # None once the account has been deleted; the words stay.
    user_id: int | None
    author_name: str | None
    author_email: str | None
    # Sent without an account, and the address they left, if any.
    signed_out: bool = False
    contact: str | None = None


class AdminFeedbackPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AdminFeedbackOut]


class FeedbackUpdateIn(BaseModel):
    status: str  # "new" | "done"


class FeedbackExportOut(BaseModel):
    """`text` is ready to paste to someone, or to Claude; no names or addresses."""

    count: int
    text: str
