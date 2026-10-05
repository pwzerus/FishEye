"""Accounts and community catch pins (docs/adr/0016-accounts-and-community-pins.md).

Kept apart from the waterbody models on purpose: everything in this file is
user-generated, and nothing in it may flow into the official tiers. A pin
can *link* to a lake (`waterbody_id`) so a lake page can show "anglers
report catching fish here", but it never becomes a WaterbodySpecies row,
never feeds the scoring engine, and never reaches the AI advisor — the same
line ADR 0012 drew for GBIF records, for the same reason.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.db.types import UTCDateTime, utcnow

ROLE_USER = "user"
ROLE_ADMIN = "admin"
USER_ACTIVE = "active"
USER_SUSPENDED = "suspended"

VISIBILITY_PUBLIC = "public"
VISIBILITY_PRIVATE = "private"

# Published immediately (the chosen policy), then possibly hidden — by
# enough reports, or by an admin — or removed by an admin.
PIN_PUBLISHED = "published"
PIN_HIDDEN = "hidden"
PIN_REMOVED = "removed"

REPORT_OPEN = "open"
REPORT_RESOLVED = "resolved"


# AUTOINCREMENT on SQLite: a deleted row's id is never handed out again, so
# nothing that outlives a row (a cached link, an audit entry) can end up
# pointing at a different user or pin. Postgres sequences behave this way
# already; the flag is ignored there.
_NO_ID_REUSE = {"sqlite_autoincrement": True}


class User(Base):
    __tablename__ = "users"
    __table_args__ = _NO_ID_REUSE

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stored lowercased and trimmed; uniqueness is on that normal form.
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(40))
    # None for accounts that have only ever signed in with Google.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_sub: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    role: Mapped[str] = mapped_column(String(16), default=ROLE_USER)
    status: Mapped[str] = mapped_column(String(16), default=USER_ACTIVE)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    sessions: Mapped[list[UserSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    pins: Mapped[list[CatchPin]] = relationship(
        back_populates="user", cascade="all, delete-orphan", foreign_keys="CatchPin.user_id"
    )

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    @property
    def is_active(self) -> bool:
        return self.status == USER_ACTIVE


class UserSession(Base):
    """A server-side session. The cookie holds a random token; only its
    SHA-256 is stored, so a leaked database can't be replayed as logins,
    and logging out or suspending a user actually ends their sessions —
    which a stateless JWT can't do before it expires."""

    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(200), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")


class CatchPin(Base):
    __tablename__ = "catch_pins"
    __table_args__ = (
        Index("ix_catch_pins_status_visibility", "status", "visibility"),
        Index("ix_catch_pins_lat_lng", "latitude", "longitude"),
        _NO_ID_REUSE,
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    title: Mapped[str] = mapped_column(String(80))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # A guide species (app/knowledge/species_guides.py) or free text for
    # anything else; both may be empty ("didn't catch anything" is a
    # useful pin too).
    species_slug: Mapped[str | None] = mapped_column(String(64), nullable=True)
    species_other: Mapped[str | None] = mapped_column(String(60), nullable=True)
    caught_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    visibility: Mapped[str] = mapped_column(String(16), default=VISIBILITY_PUBLIC)
    status: Mapped[str] = mapped_column(String(16), default=PIN_PUBLISHED)
    # Why a pin isn't published: "reports" (auto-hidden) or "moderator".
    status_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Nearest lake at the time of pinning, if one is close. A hint for the
    # UI, never evidence about the lake.
    waterbody_id: Mapped[int | None] = mapped_column(
        ForeignKey("waterbodies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="pins", foreign_keys=[user_id])
    photos: Mapped[list[PinPhoto]] = relationship(
        back_populates="pin", cascade="all, delete-orphan", order_by="PinPhoto.position"
    )
    reports: Mapped[list[PinReport]] = relationship(
        back_populates="pin", cascade="all, delete-orphan"
    )


class PinPhoto(Base):
    __tablename__ = "pin_photos"
    __table_args__ = _NO_ID_REUSE

    id: Mapped[int] = mapped_column(primary_key=True)
    pin_id: Mapped[int] = mapped_column(ForeignKey("catch_pins.id", ondelete="CASCADE"), index=True)
    # Base key in the media store; the files are <key>.jpg and <key>_thumb.jpg.
    storage_key: Mapped[str] = mapped_column(String(128), unique=True)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    bytes: Mapped[int] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    pin: Mapped[CatchPin] = relationship(back_populates="photos")


class PinReport(Base):
    __tablename__ = "pin_reports"
    # One report per person per pin: repeat reports from one account can't
    # push a pin over the auto-hide threshold.
    __table_args__ = (
        UniqueConstraint("pin_id", "reporter_id", name="uq_pin_reports_pin_reporter"),
        _NO_ID_REUSE,
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pin_id: Mapped[int] = mapped_column(ForeignKey("catch_pins.id", ondelete="CASCADE"), index=True)
    # SET NULL, not CASCADE: a reporter deleting their account mustn't erase
    # the evidence a moderator is about to look at.
    reporter_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reason: Mapped[str] = mapped_column(String(24))
    detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=REPORT_OPEN)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    resolved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # "dismissed" | "hidden" | "removed"
    resolution: Mapped[str | None] = mapped_column(String(24), nullable=True)

    pin: Mapped[CatchPin] = relationship(back_populates="reports")
    reporter: Mapped[User | None] = relationship(foreign_keys=[reporter_id])


class AuditLog(Base):
    """Every moderation and account-management action, including the
    system's own (auto-hide), so "who hid this and why" always has an
    answer."""

    __tablename__ = "audit_log"
    __table_args__ = _NO_ID_REUSE

    id: Mapped[int] = mapped_column(primary_key=True)
    # None = the system itself (e.g. auto-hide on reports).
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Who it was at the time ("Name <email>"). The log must still say who
    # acted after that account is deleted, when actor_id goes NULL.
    actor_label: Mapped[str | None] = mapped_column(String(320), nullable=True)
    action: Mapped[str] = mapped_column(String(48))
    target_type: Mapped[str] = mapped_column(String(24))
    target_id: Mapped[int] = mapped_column(Integer)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)

    actor: Mapped[User | None] = relationship(foreign_keys=[actor_id])
