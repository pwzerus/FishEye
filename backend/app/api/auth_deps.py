"""Who is making this request, and are they allowed to.

Authentication is a server-side session in an httpOnly cookie
(services/auth.py). CSRF protection is two layers:

1. The cookie is SameSite=Lax, so browsers don't attach it to cross-site
   POST/PATCH/DELETE requests at all.
2. `same_origin` rejects state-changing requests whose Origin header names
   a site other than the frontend. Browsers always send Origin on those
   requests; non-browser clients (tests, curl) that send none are allowed,
   since CSRF needs a victim's browser to work.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.models.community import User, UserSession
from app.services.auth import resolve_session

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def allowed_origins() -> set[str]:
    s = get_settings()
    return {s.frontend_origin.rstrip("/"), s.api_public_url.rstrip("/")}


def same_origin(request: Request) -> None:
    if request.method in SAFE_METHODS:
        return
    origin = request.headers.get("origin")
    if origin is not None and origin.rstrip("/") not in allowed_origins():
        raise HTTPException(status_code=403, detail="Cross-site request refused.")


@dataclass
class AuthContext:
    session: UserSession | None
    user: User | None


def get_auth(request: Request, db: Session = Depends(get_db)) -> AuthContext:
    resolved = resolve_session(db, request.cookies.get(get_settings().session_cookie_name))
    if resolved is None:
        return AuthContext(None, None)
    return AuthContext(*resolved)


def optional_user(auth: AuthContext = Depends(get_auth)) -> User | None:
    return auth.user


def require_user(auth: AuthContext = Depends(get_auth)) -> User:
    if auth.user is None:
        raise HTTPException(status_code=401, detail="Sign in to do that.")
    return auth.user


def require_admin(user: User = Depends(require_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admins only.")
    return user


def set_session_cookie(response: Response, token: str) -> None:
    s = get_settings()
    response.set_cookie(
        s.session_cookie_name,
        token,
        max_age=s.session_ttl_days * 24 * 3600,
        httponly=True,
        secure=s.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    s = get_settings()
    response.delete_cookie(
        s.session_cookie_name, path="/", httponly=True, secure=s.cookie_secure, samesite="lax"
    )
