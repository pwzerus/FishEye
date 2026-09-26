"""Password hashing, session tokens, and a small in-process rate limiter.

Passwords: scrypt from the standard library, not a third-party package.
scrypt is memory-hard and is one of the password KDFs OWASP recommends;
using hashlib's keeps the dependency list what it was. The stored string
carries its own parameters ("scrypt$n$r$p$salt$hash"), so they can be
raised later and old hashes upgraded on the next successful login
(`needs_rehash`).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import threading
import time
from collections import deque

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32
# 128 * r * n bytes ≈ 16 MiB per hash; OpenSSL's default ceiling is 32 MiB.
_SCRYPT_MAXMEM = 64 * 1024 * 1024

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
# The handful everyone tries first. Not a breach corpus — just enough that
# the demo doesn't accept the obvious ones.
_COMMON_PASSWORDS = frozenset(
    """password password1 password123 12345678 123456789 1234567890 qwerty123
    qwertyuiop iloveyou letmein1 welcome1 abc12345 11111111 00000000 fishing1
    fishmate fishmate1 bassfishing""".split()
)


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _unb64(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int, dklen: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=dklen, maxmem=_SCRYPT_MAXMEM
    )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = _scrypt(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P, SCRYPT_DKLEN)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str | None) -> bool:
    """Constant-time check. A missing or malformed hash is simply False."""
    if not stored:
        return False
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = _unb64(digest)
        actual = _scrypt(password, _unb64(salt), int(n), int(r), int(p), len(expected))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def burn_verify_time(password: str) -> None:
    """Spend the same time a real check would. Called when the email isn't
    registered, so response time doesn't reveal which emails have accounts."""
    verify_password(password, _DUMMY_HASH)


def needs_rehash(stored: str) -> bool:
    try:
        _, n, r, p, _, _ = stored.split("$")
        return (int(n), int(r), int(p)) != (SCRYPT_N, SCRYPT_R, SCRYPT_P)
    except ValueError:
        return True


def password_problem(password: str, email: str | None = None) -> str | None:
    """Why a new password is unacceptable, or None. Length over composition
    rules, per NIST SP 800-63B: rules like "one symbol" make passwords
    harder to remember without making them much harder to guess."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Use at least {MIN_PASSWORD_LENGTH} characters."
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"Use at most {MAX_PASSWORD_LENGTH} characters."
    if not password.strip():
        return "The password can't be only spaces."
    if password.lower() in _COMMON_PASSWORDS:
        return "That password is too common. Pick something less guessable."
    if email and password.lower() == email.lower():
        return "The password can't be your email address."
    return None


def new_token() -> str:
    """256 bits from the OS CSPRNG, URL-safe."""
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class RateLimiter:
    """Sliding-window counter per key, in process memory.

    Same scope caveat as the circuit breakers elsewhere: right for a
    single-process demo; a multi-worker deployment needs a shared store
    (Redis) or every worker gets its own allowance.
    """

    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float] | None:
        q = self._hits.get(key)
        if q is None:
            return None
        while q and now - q[0] >= self.window:
            q.popleft()
        if not q:
            # Evicted, so a stream of never-repeated keys (every login
            # attempt with a new email) can't grow memory without bound.
            del self._hits[key]
            return None
        return q

    def blocked_for(self, key: str) -> float:
        """Seconds until `key` may try again; 0 if it may now. Checking
        never creates an entry."""
        now = time.monotonic()
        with self._lock:
            q = self._prune(key, now)
            if q is None or len(q) < self.limit:
                return 0.0
            return max(0.0, self.window - (now - q[0]))

    def hit(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._prune(key, now)
            if q is None:
                q = self._hits[key] = deque()
            q.append(now)

    def __len__(self) -> int:
        return len(self._hits)

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)
