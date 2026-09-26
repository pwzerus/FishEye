"""Accounts: registration, password login, sessions, and Google sign-in.

Every failure is an `AuthError` carrying an HTTP status and a message that
is safe to show a user. Messages never reveal more than the user already
knows — a wrong password and an unknown email get the same answer.
"""
from __future__ import annotations

import base64
import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlencode

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    burn_verify_time,
    hash_password,
    needs_rehash,
    new_token,
    password_problem,
    token_digest,
    verify_password,
)
from app.db.types import utcnow
from app.models.community import (
    ROLE_ADMIN,
    ROLE_USER,
    USER_ACTIVE,
    User,
    UserSession,
)

# Deliberately loose: one @, something on each side, a dot in the domain.
# Real validation is "can this person receive mail there", which needs an
# email round-trip this demo doesn't have.
_EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
# Refresh last_seen_at at most this often, so reading pages doesn't turn
# into a database write per request.
_TOUCH_INTERVAL = timedelta(hours=1)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_TIMEOUT_SECONDS = 8.0


class AuthError(Exception):
    def __init__(self, status: int, message: str, code: str = "auth_error") -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.code = code


# --------------------------------------------------------------- inputs


def normalize_email(email: str) -> str:
    return email.strip().lower()


def clean_display_name(name: str) -> str:
    """Trim, collapse whitespace, and refuse control characters (which
    render as nothing and can be used to impersonate another name)."""
    name = " ".join(name.split())
    if any(unicodedata.category(ch).startswith("C") for ch in name):
        raise AuthError(422, "Display names can't contain control characters.", "bad_name")
    if not 2 <= len(name) <= 40:
        raise AuthError(422, "Display names are 2 to 40 characters.", "bad_name")
    return name


def check_email(email: str) -> str:
    email = normalize_email(email)
    if len(email) > 254 or not _EMAIL_RE.match(email):
        raise AuthError(422, "That doesn't look like an email address.", "bad_email")
    return email


def check_new_password(password: str, email: str | None) -> None:
    problem = password_problem(password, email)
    if problem:
        raise AuthError(422, problem, "weak_password")


# ------------------------------------------------------------- accounts


def register(db: Session, email: str, password: str, display_name: str) -> User:
    email = check_email(email)
    name = clean_display_name(display_name)
    check_new_password(password, email)
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        # Revealing that an address is registered is unavoidable at sign-up
        # (the alternative is a confirmation email this demo can't send);
        # login, the endpoint worth brute-forcing, doesn't reveal it.
        raise AuthError(409, "An account with this email already exists. Sign in instead.", "email_taken")
    # Registering signs you in, so it counts as a sign-in.
    user = User(
        email=email,
        display_name=name,
        password_hash=hash_password(password),
        role=ROLE_USER,
        last_login_at=utcnow(),
    )
    db.add(user)
    db.flush()
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None or user.password_hash is None:
        burn_verify_time(password)
        raise AuthError(401, "Email or password is incorrect.", "bad_credentials")
    if not verify_password(password, user.password_hash):
        raise AuthError(401, "Email or password is incorrect.", "bad_credentials")
    if not user.is_active:
        raise AuthError(403, "This account is suspended.", "suspended")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.last_login_at = utcnow()
    return user


def change_password(db: Session, user: User, current: str | None, new: str) -> None:
    if user.password_hash is not None and not verify_password(current or "", user.password_hash):
        raise AuthError(403, "Your current password is incorrect.", "bad_credentials")
    check_new_password(new, user.email)
    user.password_hash = hash_password(new)


def active_admin_count(db: Session) -> int:
    return db.scalar(
        select(func.count(User.id)).where(User.role == ROLE_ADMIN, User.status == USER_ACTIVE)
    ) or 0


def is_last_admin(db: Session, user: User) -> bool:
    return user.is_admin and user.is_active and active_admin_count(db) <= 1


# ------------------------------------------------------------- sessions


def create_session(db: Session, user: User, user_agent: str | None = None) -> str:
    """Returns the raw token for the cookie. Only its digest is stored."""
    token = new_token()
    now = utcnow()
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=token_digest(token),
            created_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(days=get_settings().session_ttl_days),
            user_agent=(user_agent or "")[:200] or None,
        )
    )
    return token


def resolve_session(db: Session, token: str | None) -> tuple[UserSession, User] | None:
    if not token or len(token) > 200:
        return None
    session = db.scalar(select(UserSession).where(UserSession.token_hash == token_digest(token)))
    now = utcnow()
    if session is None or session.revoked_at is not None or session.expires_at <= now:
        return None
    user = session.user
    if not user.is_active:
        return None
    if now - session.last_seen_at > _TOUCH_INTERVAL:
        session.last_seen_at = now
        db.commit()
    return session, user


def revoke_session(db: Session, session: UserSession) -> None:
    session.revoked_at = utcnow()


def revoke_all_sessions(db: Session, user: User, keep: UserSession | None = None) -> int:
    now = utcnow()
    count = 0
    for s in user.sessions:
        if s.revoked_at is None and (keep is None or s.id != keep.id):
            s.revoked_at = now
            count += 1
    return count


# --------------------------------------------------------------- Google


def google_enabled() -> bool:
    s = get_settings()
    return bool(s.google_client_id and s.google_client_secret)


def google_redirect_uri() -> str:
    return f"{get_settings().api_public_url.rstrip('/')}/api/auth/google/callback"


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def google_auth_url(state: str, verifier: str) -> str:
    params = {
        "client_id": get_settings().google_client_id,
        "redirect_uri": google_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": pkce_challenge(verifier),
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


@dataclass(frozen=True)
class GoogleProfile:
    sub: str
    email: str
    name: str


def google_profile(code: str, verifier: str) -> GoogleProfile:
    """Exchange the authorization code and read the user's profile.

    The profile comes from Google's userinfo endpoint using the access
    token this server just received directly from Google over TLS, in
    exchange for a code plus our client secret. That's what makes it
    trustworthy without verifying an ID-token signature ourselves.
    """
    s = get_settings()
    try:
        with httpx.Client(timeout=GOOGLE_TIMEOUT_SECONDS) as client:
            token_resp = client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": s.google_client_id,
                    "client_secret": s.google_client_secret,
                    "redirect_uri": google_redirect_uri(),
                    "grant_type": "authorization_code",
                    "code_verifier": verifier,
                },
            )
            token_resp.raise_for_status()
            access_token = token_resp.json()["access_token"]
            info_resp = client.get(
                GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
            )
            info_resp.raise_for_status()
            info = info_resp.json()
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise AuthError(502, "Google sign-in didn't complete. Try again.", "google_failed") from exc

    if not info.get("sub") or not info.get("email"):
        raise AuthError(502, "Google didn't return an email address.", "google_failed")
    if info.get("email_verified") is not True:
        raise AuthError(403, "Your Google email address isn't verified.", "google_unverified")
    name = " ".join(str(info.get("name") or info["email"].split("@")[0]).split())[:40]
    return GoogleProfile(sub=str(info["sub"]), email=normalize_email(info["email"]), name=name)


def google_sign_in(db: Session, profile: GoogleProfile, current: User | None) -> User:
    """Sign in, connect, or create — without ever silently merging accounts.

    - Known Google account: sign in as its owner.
    - Signed in already: connect Google to the current account.
    - Email matches an existing FishMate account: refuse. Local emails are
      never verified here, so auto-linking would hand a password-holder's
      account to whoever controls the Google address, or the reverse. The
      owner signs in with their password and connects Google from the
      account page instead.
    - Otherwise: a new account with no password.
    """
    by_sub = db.scalar(select(User).where(User.google_sub == profile.sub))
    if current is not None:
        if by_sub is not None and by_sub.id != current.id:
            raise AuthError(409, "That Google account is connected to a different FishMate account.", "google_in_use")
        current.google_sub = profile.sub
        return current
    if by_sub is not None:
        if not by_sub.is_active:
            raise AuthError(403, "This account is suspended.", "suspended")
        by_sub.last_login_at = utcnow()
        return by_sub
    if db.scalar(select(User.id).where(User.email == profile.email)) is not None:
        raise AuthError(409, "Sign in with your password, then connect Google from your account page.", "google_email_exists")
    try:
        name = clean_display_name(profile.name)
    except AuthError:
        name = "Angler"
    user = User(email=profile.email, display_name=name, google_sub=profile.sub, last_login_at=utcnow())
    db.add(user)
    db.flush()
    return user
