from collections.abc import Generator

from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

_is_sqlite = settings.database_url.startswith("sqlite")

if _is_sqlite:
    # One file, many FastAPI threads: SQLite would otherwise refuse a
    # connection used off the thread that opened it.
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
else:
    # A hosted Postgres (Neon, Supabase, RDS…) drops connections that have
    # been idle — on the serverless ones, aggressively. Without pre_ping the
    # first request after a quiet spell fails on a dead pooled connection
    # instead of transparently opening a new one. pool_recycle keeps this
    # side of the pool younger than any sensible server-side idle timeout.
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=300,
    )


def enforce_sqlite_foreign_keys(target: Engine) -> None:
    """SQLite ignores FOREIGN KEY clauses unless each connection opts in.
    Without this, deleting a user left their reports and audit entries
    pointing at an id the next sign-up would reuse (ADR 0016)."""
    if target.dialect.name != "sqlite":
        return

    @event.listens_for(target, "connect")
    def _fk_on(dbapi_connection: Any, _record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


enforce_sqlite_foreign_keys(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
