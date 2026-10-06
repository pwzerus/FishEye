"""/api/auth — accounts, sessions, and optional Google sign-in."""
from __future__ import annotations

import hmac
from datetime import timedelta
from typing import NoReturn
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.auth_deps import (
    AuthContext,
    clear_session_cookie,
    get_auth,
    require_user,
    same_origin,
    set_session_cookie,
)
from app.api.deps import get_db
from app.api.rate_limits import client_ip
from app.core.config import get_settings
from app.core.security import RateLimiter, new_token, verify_password
from app.db.types import utcnow
from app.models.community import User
from app.schemas.auth import (
    DeleteAccountIn,
    ReauthIn,
    LoginIn,
    PasswordChangeIn,
    ProfileIn,
    ProvidersOut,
    RegisterIn,
    SessionOut,
    UserOut,
)
from app.services import audit
from app.services import auth as auth_service
from app.services import pins as pin_service
from app.services.auth import AuthError
from app.services.media import get_store

router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(same_origin)])

# Per email: slows guessing one account. Per IP: slows spraying many.
login_by_email = RateLimiter(limit=8, window_seconds=15 * 60)
login_by_ip = RateLimiter(limit=40, window_seconds=15 * 60)
register_by_ip = RateLimiter(limit=10, window_seconds=60 * 60)

OAUTH_COOKIE = "fm_oauth"
OAUTH_COOKIE_TTL = 10 * 60
# Changes that could lock the real owner out (setting a Google-only
# account's first password, disconnecting Google, connecting a Google
# account, deleting a passwordless account) need a session this young. A
# stolen, days-old cookie can browse; it can't take the account over.
FRESH_SESSION = timedelta(minutes=15)
REAUTH_MESSAGE = "For your security, confirm it's you first."


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        status=user.status,
        has_password=user.password_hash is not None,
        google_connected=user.google_sub is not None,
        created_at=user.created_at,
    )


def _is_fresh(auth: AuthContext) -> bool:
    return auth.session is not None and utcnow() - auth.session.created_at <= FRESH_SESSION


def _require_fresh(auth: AuthContext) -> None:
    if not _is_fresh(auth):
        raise HTTPException(status_code=403, detail=REAUTH_MESSAGE, headers={"X-Reauth-Required": "1"})


def _raise(exc: AuthError) -> NoReturn:
    raise HTTPException(status_code=exc.status, detail=exc.message) from exc


def _throttle(limiter: RateLimiter, key: str) -> None:
    wait = limiter.blocked_for(key)
    if wait > 0:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Wait a few minutes and try again.",
            headers={"Retry-After": str(int(wait) + 1)},
        )


@router.get("/providers", response_model=ProvidersOut)
def providers() -> ProvidersOut:
    return ProvidersOut(password=True, google=auth_service.google_enabled())


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)) -> UserOut:
    ip = client_ip(request)
    _throttle(register_by_ip, ip)
    register_by_ip.hit(ip)
    try:
        user = auth_service.register(db, payload.email, payload.password, payload.display_name)
    except AuthError as exc:
        _raise(exc)
    token = auth_service.create_session(db, user, request.headers.get("user-agent"))
    db.commit()
    set_session_cookie(response, token)
    return user_out(user)


@router.post("/login", response_model=UserOut)
def login(payload: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)) -> UserOut:
    email_key = auth_service.normalize_email(payload.email)
    ip = client_ip(request)
    _throttle(login_by_email, email_key)
    _throttle(login_by_ip, ip)
    try:
        user = auth_service.authenticate(db, payload.email, payload.password)
    except AuthError as exc:
        if exc.code == "bad_credentials":
            login_by_email.hit(email_key)
            login_by_ip.hit(ip)
        _raise(exc)
    login_by_email.reset(email_key)
    token = auth_service.create_session(db, user, request.headers.get("user-agent"))
    db.commit()
    set_session_cookie(response, token)
    return user_out(user)


@router.post("/logout", status_code=204, response_class=Response)
def logout(response: Response, auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)) -> Response:
    if auth.session is not None:
        auth_service.revoke_session(db, auth.session)
        db.commit()
    clear_session_cookie(response)
    response.status_code = 204
    return response


@router.get("/session", response_model=SessionOut)
def session(auth: AuthContext = Depends(get_auth)) -> SessionOut:
    """Who is signed in, for the UI's first paint. Unlike /me this never
    401s: a signed-out visitor is the common case, and every page load
    shouldn't log an error in their console."""
    return SessionOut(user=user_out(auth.user) if auth.user else None)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(require_user)) -> UserOut:
    return user_out(user)


@router.post("/reauth", response_model=UserOut)
def reauth(
    payload: ReauthIn,
    request: Request,
    response: Response,
    auth: AuthContext = Depends(get_auth),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> UserOut:
    """Confirm the password to get a fresh session (the old one is
    replaced). Google-only accounts re-authenticate by signing in with
    Google again instead."""
    _throttle(login_by_email, user.email)
    if not verify_password(payload.password, user.password_hash):
        login_by_email.hit(user.email)
        raise HTTPException(status_code=403, detail="That password is incorrect.")
    if auth.session is not None:
        auth_service.revoke_session(db, auth.session)
    token = auth_service.create_session(db, user, request.headers.get("user-agent"))
    db.commit()
    set_session_cookie(response, token)
    return user_out(user)


@router.patch("/me", response_model=UserOut)
def update_me(payload: ProfileIn, user: User = Depends(require_user), db: Session = Depends(get_db)) -> UserOut:
    try:
        user.display_name = auth_service.clean_display_name(payload.display_name)
    except AuthError as exc:
        _raise(exc)
    db.commit()
    return user_out(user)


@router.post("/me/password", response_model=UserOut)
def change_password(
    payload: PasswordChangeIn,
    auth: AuthContext = Depends(get_auth),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> UserOut:
    if user.password_hash is None:
        _require_fresh(auth)
    try:
        auth_service.change_password(db, user, payload.current_password, payload.new_password)
    except AuthError as exc:
        _raise(exc)
    # Anyone else holding a session (a stolen one included) is signed out;
    # this browser stays signed in.
    auth_service.revoke_all_sessions(db, user, keep=auth.session)
    db.commit()
    return user_out(user)


@router.post("/me/google/disconnect", response_model=UserOut)
def disconnect_google(
    auth: AuthContext = Depends(get_auth), user: User = Depends(require_user), db: Session = Depends(get_db)
) -> UserOut:
    _require_fresh(auth)
    if user.password_hash is None:
        raise HTTPException(status_code=409, detail="Set a password first, or you'd have no way to sign in.")
    user.google_sub = None
    db.commit()
    return user_out(user)


@router.delete("/me", status_code=204, response_class=Response)
def delete_me(
    payload: DeleteAccountIn,
    response: Response,
    auth: AuthContext = Depends(get_auth),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> Response:
    if user.password_hash is None:
        _require_fresh(auth)
    elif not verify_password(payload.password or "", user.password_hash):
        raise HTTPException(status_code=403, detail="Your password is incorrect.")
    if auth_service.is_last_admin(db, user):
        raise HTTPException(status_code=409, detail="You're the only admin. Make someone else an admin first.")
    keys = pin_service.photo_keys_of(user)
    # Logged before the row goes; the entry keeps "name <email>" as its
    # actor label once actor_id is nulled by the delete.
    audit.record(db, user, "user.deleted", "user", user.id, pins=len(user.pins))
    db.delete(user)  # sessions, pins and their photos cascade; reports they filed keep a NULL reporter
    db.commit()
    store = get_store()
    for key in keys:
        store.delete(key)
    clear_session_cookie(response)
    response.status_code = 204
    return response


# ------------------------------------------------------------ Google


def _safe_next(path: str | None) -> str:
    """Only same-site relative paths of plain visible ASCII: never an open
    redirect, and nothing that can't go in a cookie or a Location header."""
    if (
        not path
        or not path.startswith("/")
        or path.startswith("//")
        or "\\" in path
        or "|" in path
        or len(path) > 200
        or any(not ("!" <= ch <= "~") for ch in path)
    ):
        return "/account"
    return path


def _frontend(path: str, **query: str) -> str:
    base = get_settings().frontend_origin.rstrip("/")
    return f"{base}{path}" + (f"?{urlencode(query)}" if query else "")


@router.get("/google/start")
def google_start(next_path: str | None = Query(default=None, alias="next")) -> RedirectResponse:
    if not auth_service.google_enabled():
        raise HTTPException(status_code=404, detail="Google sign-in isn't configured.")
    state, verifier = new_token(), new_token()
    resp = RedirectResponse(auth_service.google_auth_url(state, verifier), status_code=302)
    s = get_settings()
    # State, PKCE verifier and return path ride in one short-lived httpOnly
    # cookie. Lax is enough: Google's redirect back is a top-level GET.
    resp.set_cookie(
        OAUTH_COOKIE,
        f"{state}|{verifier}|{_safe_next(next_path)}",
        max_age=OAUTH_COOKIE_TTL,
        httponly=True,
        secure=s.cookie_secure,
        samesite="lax",
        path="/api/auth/google",
    )
    return resp


@router.get("/google/callback")
def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    auth: AuthContext = Depends(get_auth),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    cookie = request.cookies.get(OAUTH_COOKIE, "")
    parts = cookie.split("|", 2)

    def fail(code_: str) -> RedirectResponse:
        target = "/account" if auth.user else "/login"
        r = RedirectResponse(_frontend(target, error=code_), status_code=302)
        r.delete_cookie(OAUTH_COOKIE, path="/api/auth/google")
        return r

    if not auth_service.google_enabled():
        return fail("google_disabled")
    if error:
        return fail("google_cancelled")
    if len(parts) != 3 or not state or not code:
        return fail("google_state")
    if not hmac.compare_digest(parts[0].encode("utf-8"), state.encode("utf-8")):
        return fail("google_state")
    _, verifier, next_path = parts
    # The cookie was set by us, but re-check anyway: a cookie can be planted
    # by a sibling subdomain or over plain HTTP.
    next_path = _safe_next(next_path)
    try:
        profile = auth_service.google_profile(code, verifier)
    except AuthError as exc:
        return fail(exc.code)

    current = auth.user
    reauth = current is not None and current.google_sub == profile.sub
    if current is not None and not reauth and not _is_fresh(auth):
        # Connecting a *new* Google account to an existing one is an
        # account-recovery path, so a stale (possibly stolen) session
        # can't do it.
        return fail("reauth_required")
    try:
        user = auth_service.google_sign_in(db, profile, None if reauth else current)
    except AuthError as exc:
        db.rollback()
        return fail(exc.code)

    connecting = current is not None and not reauth
    resp = RedirectResponse(_frontend(next_path, **({"connected": "google"} if connecting else {})), status_code=302)
    if not connecting:
        # A new sign-in, or the owner re-confirming with Google: either way a
        # fresh session replaces whatever this browser had.
        if auth.session is not None:
            auth_service.revoke_session(db, auth.session)
        token = auth_service.create_session(db, user, request.headers.get("user-agent"))
        set_session_cookie(resp, token)
    db.commit()
    resp.delete_cookie(OAUTH_COOKIE, path="/api/auth/google")
    return resp
