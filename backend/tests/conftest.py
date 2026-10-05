import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.api.deps import get_db  # noqa: E402
from app.db.session import Base, enforce_sqlite_foreign_keys  # noqa: E402
from app.db.spatial import ensure_spatial_schema  # noqa: E402
from app.main import app  # noqa: E402
from app.models.waterbody import (  # noqa: E402
    AccessPoint,
    Species,
    State,
    Waterbody,
    WaterbodySpecies,
)

# In-memory SQLite by default: no setup, and every test gets a clean file.
# Point TEST_DATABASE_URL at a PostgreSQL database to run this same suite
# against the deployment database instead — the one way to find out before
# a release that a query only ever worked because of SQLite's laxness. e.g.
#   TEST_DATABASE_URL=postgresql+psycopg://user:pw@localhost/fisheye_test pytest
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")
_TEST_IS_SQLITE = TEST_DATABASE_URL.startswith("sqlite")

if _TEST_IS_SQLITE:
    TEST_ENGINE = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        # One shared connection, so ":memory:" is one database rather than a
        # fresh empty one per checkout.
        poolclass=StaticPool,
    )
else:
    TEST_ENGINE = create_engine(TEST_DATABASE_URL)
enforce_sqlite_foreign_keys(TEST_ENGINE)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=TEST_ENGINE)
    # Re-run per test: create_all above has just rebuilt waterbodies, so its
    # PostGIS column and index need adding back. A no-op on SQLite.
    ensure_spatial_schema(TEST_ENGINE)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_lake(db_session):
    """One state, one waterbody, one confirmed species, one access point —
    the minimum fixture that exercises joins/filters without pulling in the
    full seed script."""
    tx = State(name="Texas", code="TX", official_source_url="https://tpwd.texas.gov")
    db_session.add(tx)
    db_session.flush()

    bass = Species(
        common_name="Largemouth Bass",
        scientific_name="Micropterus salmoides",
        difficulty="beginner",
        profile="test profile",
    )
    db_session.add(bass)
    db_session.flush()

    wb = Waterbody(
        state_id=tx.id,
        name="Lake Fork",
        latitude=32.8065,
        longitude=-95.5931,
        access_summary="test summary",
        source_url="https://tpwd.texas.gov/fork",
        source_updated_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        field_tested=True,
    )
    db_session.add(wb)
    db_session.flush()

    db_session.add(
        WaterbodySpecies(
            waterbody_id=wb.id,
            species_id=bass.id,
            confidence="confirmed",
            evidence="test evidence",
            source_url="https://tpwd.texas.gov/fork",
            observed_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
    )
    db_session.add(
        AccessPoint(
            waterbody_id=wb.id,
            name="Lake Fork Dam Bank Access",
            latitude=32.8330,
            longitude=-95.5670,
            access_type="bank",
            public_status="confirmed_public",
            parking=True,
        )
    )
    db_session.commit()
    return {"state": tx, "waterbody": wb, "species": bass}


# --------------------------------------------------------------------------
# Accounts and community pins
# --------------------------------------------------------------------------


@pytest.fixture()
def make_client(db_session):
    """A fresh client per call — its own cookie jar, i.e. its own browser —
    all sharing the test database."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    clients = []

    def _make() -> TestClient:
        c = TestClient(app)
        clients.append(c)
        return c

    yield _make
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _isolated_community_state(tmp_path, monkeypatch):
    """Photos go to a temp folder, and in-memory rate limits start empty,
    for every test."""
    from app.api import auth as auth_api
    from app.api import pins as pins_api
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "media_root", str(tmp_path / "media"))
    for limiter in (
        auth_api.login_by_email,
        auth_api.login_by_ip,
        auth_api.register_by_ip,
        pins_api.create_by_user,
        pins_api.report_by_user,
    ):
        limiter.reset()
    yield


def signup(client: TestClient, email: str = "angler@example.com", name: str = "Angler", password: str = "tight-lines-42"):
    resp = client.post("/api/auth/register", json={"email": email, "password": password, "display_name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()


def make_admin(db_session, email: str) -> None:
    from sqlalchemy import select

    from app.models.community import ROLE_ADMIN, User

    user = db_session.scalar(select(User).where(User.email == email))
    user.role = ROLE_ADMIN
    db_session.commit()
