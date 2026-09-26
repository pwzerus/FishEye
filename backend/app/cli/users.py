"""Account administration from the command line.

    python -m app.cli.users create-admin --email you@example.com --name "Your Name"
    python -m app.cli.users promote --email someone@example.com
    python -m app.cli.users demote --email someone@example.com
    python -m app.cli.users list

The first admin can only be made here, by someone with shell access to the
server. There is deliberately no "first user to sign up becomes admin"
rule and no web endpoint that grants the role without an existing admin:
either would make the admin panel the prize of whoever registers first.
Passwords are read with getpass (never a command-line argument, which
would land in shell history and the process list).
"""
from __future__ import annotations

import argparse
import getpass
import sys

from sqlalchemy import select

import app.models  # noqa: F401  (register every model)
from app.db.session import Base, SessionLocal, engine
from app.models.community import ROLE_ADMIN, ROLE_USER, User
from app.services import audit
from app.services import auth as auth_service
from app.services.auth import AuthError


def _read_password() -> str:
    if not sys.stdin.isatty():
        # Piped input (scripts, CI): one line.
        return sys.stdin.readline().rstrip("\n")
    first = getpass.getpass("Password: ")
    if first != getpass.getpass("Again: "):
        raise SystemExit("Passwords didn't match.")
    return first


def create_admin(email: str, name: str) -> int:
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == auth_service.normalize_email(email)))
        if existing is not None:
            print(f"{existing.email} already has an account; use `promote` instead.")
            return 1
        try:
            user = auth_service.register(db, email, _read_password(), name)
        except AuthError as exc:
            print(exc.message)
            return 1
        user.role = ROLE_ADMIN
        audit.record(db, None, "user.created_admin_cli", "user", user.id, email=user.email)
        db.commit()
        print(f"Admin {user.email} created.")
        return 0


def set_role(email: str, role: str) -> int:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == auth_service.normalize_email(email)))
        if user is None:
            print(f"No account for {email}.")
            return 1
        if role == ROLE_USER and auth_service.is_last_admin(db, user):
            print("That's the last active admin; promote someone else first.")
            return 1
        before = user.role
        user.role = role
        audit.record(db, None, "user.role_cli", "user", user.id, role=f"{before} -> {role}")
        db.commit()
        print(f"{user.email}: {before} -> {role}")
        return 0


def list_users() -> int:
    with SessionLocal() as db:
        for u in db.scalars(select(User).order_by(User.id)):
            print(f"{u.id:>5}  {u.role:<6} {u.status:<9} {u.email}  ({u.display_name})")
    return 0


def main(argv: list[str] | None = None) -> int:
    Base.metadata.create_all(bind=engine)
    parser = argparse.ArgumentParser(prog="python -m app.cli.users", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    ca = sub.add_parser("create-admin", help="create a new admin account")
    ca.add_argument("--email", required=True)
    ca.add_argument("--name", required=True)
    for name in ("promote", "demote"):
        p = sub.add_parser(name, help=f"{name} an existing account")
        p.add_argument("--email", required=True)
    sub.add_parser("list", help="list accounts")
    args = parser.parse_args(argv)
    if args.cmd == "create-admin":
        return create_admin(args.email, args.name)
    if args.cmd == "promote":
        return set_role(args.email, ROLE_ADMIN)
    if args.cmd == "demote":
        return set_role(args.email, ROLE_USER)
    return list_users()


if __name__ == "__main__":
    sys.exit(main())
