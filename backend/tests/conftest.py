import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.api.deps import get_db  # noqa: E402
from app.db.session import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.models.waterbody import (  # noqa: E402
    AccessPoint,
    Species,
    State,
    Waterbody,
    WaterbodySpecies,
)

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=TEST_ENGINE)
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
