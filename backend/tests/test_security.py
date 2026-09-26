from datetime import datetime, timedelta, timezone

import pytest

from app.core import security
from app.db.types import UTCDateTime


def test_hash_round_trip_and_salted():
    h1 = security.hash_password("tight-lines-42")
    h2 = security.hash_password("tight-lines-42")
    assert h1 != h2  # salted
    assert h1.startswith("scrypt$16384$8$1$")
    assert security.verify_password("tight-lines-42", h1)
    assert not security.verify_password("tight-lines-43", h1)


@pytest.mark.parametrize("stored", [None, "", "garbage", "bcrypt$x$y$z$a$b", "scrypt$a$b$c$d$e"])
def test_malformed_hashes_never_verify(stored):
    assert security.verify_password("anything", stored) is False


def test_old_parameters_are_flagged_for_rehash():
    current = security.hash_password("x" * 10)
    assert not security.needs_rehash(current)
    weaker = current.replace("scrypt$16384$", "scrypt$1024$", 1)
    assert security.needs_rehash(weaker)


@pytest.mark.parametrize(
    "password, ok",
    [("short", False), ("password123", False), ("angler@example.com", False), ("        ", False), ("tight-lines-42", True)],
)
def test_password_rules(password, ok):
    assert (security.password_problem(password, "angler@example.com") is None) is ok


def test_session_tokens_are_long_random_and_only_digests_are_comparable():
    a, b = security.new_token(), security.new_token()
    assert a != b and len(a) >= 43
    assert security.token_digest(a) != a and len(security.token_digest(a)) == 64


def test_rate_limiter_blocks_after_limit_and_can_be_reset():
    rl = security.RateLimiter(limit=2, window_seconds=60)
    assert rl.blocked_for("k") == 0
    rl.hit("k")
    rl.hit("k")
    assert rl.blocked_for("k") > 0
    assert rl.blocked_for("other") == 0
    rl.reset("k")
    assert rl.blocked_for("k") == 0


def test_utc_column_round_trips_aware_and_refuses_naive():
    col = UTCDateTime()
    cdt = timezone(timedelta(hours=-5))
    stored = col.process_bind_param(datetime(2026, 9, 25, 7, 0, tzinfo=cdt), None)
    assert stored == datetime(2026, 9, 25, 12, 0)  # naive UTC
    back = col.process_result_value(stored, None)
    assert back == datetime(2026, 9, 25, 12, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        col.process_bind_param(datetime(2026, 9, 25), None)
