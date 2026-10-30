"""Confirming that an account's email address is really its owner's.

Off until outgoing mail is set up (EMAIL_VERIFICATION=on with
MAIL_BACKEND=smtp, services/mail.py). When on:
- signing up emails a link to /verify-email?token=…, good for
  `email_token_hours`; the account page can send another;
- an account that hasn't confirmed can browse, ask and keep its account,
  but can't share or report catches (`require_verified`), so an address
  nobody owns can't be used to post or to pile reports onto a catch;
- Google sign-ins come confirmed: Google only signs in verified addresses
  (services/auth.google_profile refuses the rest);
- admins are never held back.

Like sessions, the link's token is stored only as its SHA-256.
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import new_token, token_digest
from app.db.types import utcnow
from app.models.community import EmailToken, User
from app.services import mail

VERIFY_FIRST = "Confirm your email address first: open the link we emailed you, or send a new one from your account page."


class VerificationError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def enabled() -> bool:
    return get_settings().email_verification == "on"


def needs_verifying(user: User) -> bool:
    """Is this account held back until it confirms its address?"""
    return enabled() and not user.is_admin and user.email_verified_at is None


def require_verified(user: User) -> None:
    if needs_verifying(user):
        raise VerificationError(403, VERIFY_FIRST)


def mark_verified(user: User) -> None:
    if user.email_verified_at is None:
        user.email_verified_at = utcnow()


def send_link(db: Session, user: User) -> None:
    """Email a fresh confirmation link; earlier links stop working. Raises
    mail.MailError when the message couldn't be sent."""
    s = get_settings()
    token = new_token()
    now = utcnow()
    db.execute(delete(EmailToken).where(EmailToken.user_id == user.id))
    db.add(
        EmailToken(
            user_id=user.id,
            token_hash=token_digest(token),
            created_at=now,
            expires_at=now + timedelta(hours=s.email_token_hours),
        )
    )
    db.flush()
    link = f"{s.frontend_origin.rstrip('/')}/verify-email?token={token}"
    mail.send(
        user.email,
        "Confirm your email for FishEye",
        f"Hi {user.display_name},\n\n"
        f"Confirm this is your email address so you can share catches on FishEye:\n\n{link}\n\n"
        f"The link works for {s.email_token_hours} hours. If you didn't sign up for FishEye, "
        "ignore this email and nothing will happen.\n\n— FishEye\n",
    )


def confirm(db: Session, token: str) -> User:
    """The account a link belongs to, now confirmed. A link works once."""
    row = db.scalar(select(EmailToken).where(EmailToken.token_hash == token_digest(token or "")))
    if row is None:
        raise VerificationError(400, "This link has already been used or isn't valid. Send a new one from your account page.")
    if row.expires_at <= utcnow():
        db.delete(row)
        raise VerificationError(400, "This link has expired. Send a new one from your account page.")
    user = db.get(User, row.user_id)
    db.delete(row)
    if user is None:
        raise VerificationError(400, "This link isn't valid any more.")
    mark_verified(user)
    return user
