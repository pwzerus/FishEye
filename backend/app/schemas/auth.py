from datetime import datetime

from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)
    display_name: str = Field(max_length=80)


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)


class ReauthIn(BaseModel):
    password: str = Field(max_length=256)


class ProfileIn(BaseModel):
    display_name: str = Field(max_length=80)


class PasswordChangeIn(BaseModel):
    # Required when the account has a password; Google-only accounts set
    # their first password without one.
    current_password: str | None = Field(default=None, max_length=256)
    new_password: str = Field(max_length=256)


class DeleteAccountIn(BaseModel):
    password: str | None = Field(default=None, max_length=256)


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    status: str
    has_password: bool
    google_connected: bool
    created_at: datetime
    email_verified: bool = False
    # True while the account must confirm its email before sharing or
    # reporting catches (EMAIL_VERIFICATION=on, services/email_verification.py).
    verification_required: bool = False


class VerifyEmailIn(BaseModel):
    token: str = Field(max_length=200)


class VerifyEmailOut(BaseModel):
    verified: bool
    email: str


class ProvidersOut(BaseModel):
    password: bool
    google: bool


class SessionOut(BaseModel):
    """`user` is null when signed out — a normal answer, not an error."""

    user: UserOut | None
