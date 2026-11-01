"""Display names and catches the word filter would refuse today.

    python -m app.cli.word_check

The filter (services/word_filter.py) checks a name or a catch when it is
written, so what was saved before it existed, or before a word was added
to it, stays until someone edits it. This lists those, for an admin to
deal with in the admin console: hide or remove the catch, suspend the
account. It changes nothing.
"""
from __future__ import annotations

import sys

from sqlalchemy import select

import app.models  # noqa: F401  (register every model)
from app.db.session import SessionLocal
from app.models.community import CatchPin, User
from app.services.word_filter import blocked_word


def main() -> int:
    found = 0
    with SessionLocal() as db:
        for user in db.scalars(select(User).order_by(User.id)):
            if word := blocked_word(user.display_name):
                found += 1
                print(f"user {user.id} ({user.email}, {user.status}): display name has {word!r}")
        for pin in db.scalars(select(CatchPin).order_by(CatchPin.id)):
            for field in ("title", "note", "species_other"):
                if word := blocked_word(getattr(pin, field)):
                    found += 1
                    print(f"catch {pin.id} ({pin.visibility}, {pin.status}, user {pin.user_id}): {field} has {word!r}")
    print(f"{found} found." if found else "Nothing found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
