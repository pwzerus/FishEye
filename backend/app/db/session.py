from collections.abc import Generator

from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)


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
