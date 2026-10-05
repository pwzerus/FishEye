"""A small, self-contained eval database.

Deliberately not a subset of the real seed script: the eval suite needs to
know *exactly* what's in the database (which species are confirmed where,
which lake is closed) so each case's expectation is derivable by inspection,
not by reading whatever the current TPWD scrape happens to contain.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.models.waterbody import AccessPoint, Species, State, Waterbody, WaterbodySpecies

CONFIRMED_SPECIES = "Largemouth Bass"
# Exists in the system's vocabulary but is never linked to either lake below.
# Two cases need exactly this: asking about a species that isn't confirmed
# here (a legitimate negative match, not a grounding failure), and forcing
# the mock provider's FAILURE_HALLUCINATED_SPECIES path to name a fish the
# grounding check must reject.
UNCONFIRMED_SPECIES = "Peacock Bass"


@dataclass(frozen=True)
class EvalFixtureIds:
    open_lake_id: int
    closed_lake_id: int


def build_eval_db() -> tuple[Session, EvalFixtureIds]:
    """A fresh in-memory database with one open lake and one closed lake.

    Returns an open Session the caller is responsible for closing, plus the
    waterbody ids each EvalCase refers to by name ("open" / "closed") rather
    than by a magic number.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db: Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    tx = State(name="Texas", code="TX", official_source_url="https://tpwd.texas.gov")
    db.add(tx)
    db.flush()

    bass = Species(
        common_name=CONFIRMED_SPECIES,
        scientific_name="Micropterus salmoides",
        difficulty="beginner",
        profile="eval fixture",
    )
    peacock = Species(
        common_name=UNCONFIRMED_SPECIES,
        scientific_name="Cichla ocellaris",
        difficulty="advanced",
        profile="not present in Texas — eval fixture for the grounding check",
    )
    db.add_all([bass, peacock])
    db.flush()

    open_lake = Waterbody(
        state_id=tx.id,
        name="Eval Lake Open",
        latitude=32.8065,
        longitude=-95.5931,
        access_summary="eval fixture — open lake",
        source_url="https://tpwd.texas.gov/eval-lake-open",
        source_updated_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        field_tested=True,
        public_access_status="open",
    )
    closed_lake = Waterbody(
        state_id=tx.id,
        name="Eval Lake Closed",
        latitude=30.7749,
        longitude=-96.1297,
        access_summary="eval fixture — closed to the public, per its source",
        source_url="https://tpwd.texas.gov/eval-lake-closed",
        source_updated_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        field_tested=False,
        public_access_status="closed",
    )
    db.add_all([open_lake, closed_lake])
    db.flush()

    db.add(
        WaterbodySpecies(
            waterbody_id=open_lake.id,
            species_id=bass.id,
            confidence="confirmed",
            evidence="eval fixture evidence sentence",
            source_url="https://tpwd.texas.gov/eval-lake-open",
            observed_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
    )
    db.add(
        AccessPoint(
            waterbody_id=open_lake.id,
            name="Eval Lake Open Boat Ramp",
            latitude=32.8330,
            longitude=-95.5670,
            access_type="boat_ramp",
            public_status="confirmed_public",
            parking=True,
        )
    )
    # The closed lake gets zero access points, on purpose: PRD constraint 12
    # forbids inventing public access for a lake whose own source says it's
    # closed, so "closed" and "zero access points" are always true together
    # here.

    db.commit()
    return db, EvalFixtureIds(open_lake_id=open_lake.id, closed_lake_id=closed_lake.id)
