"""Core waterbody/species domain models.

Design note (see docs/adr/0001-defer-postgis.md): coordinates are plain
lat/lng floats for the MVP rather than PostGIS geometry columns. The PRD
calls for PostGIS to support shoreline/polygon analysis later (satellite
imagery features, contour-based structure detection); none of the MVP
scoring signals need real geometry yet, and requiring PostGIS pushes
first-run friction onto anyone trying the demo. Swapping AccessPoint.lat/lng
and Waterbody bounding info for geometry columns later is a additive
migration, not a rewrite.
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class State(Base):
    __tablename__ = "states"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    code: Mapped[str] = mapped_column(String(2), unique=True)  # e.g. "TX"
    official_source_url: Mapped[str] = mapped_column(String(512))

    waterbodies: Mapped[list["Waterbody"]] = relationship(back_populates="state")


class Waterbody(Base):
    __tablename__ = "waterbodies"

    id: Mapped[int] = mapped_column(primary_key=True)
    state_id: Mapped[int] = mapped_column(ForeignKey("states.id"))
    name: Mapped[str] = mapped_column(String(128))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    access_summary: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(512))
    source_updated_at: Mapped[datetime] = mapped_column(DateTime)
    # True only for the handful of lakes prioritized for real friend
    # field-testing per PRD §12.1 — shown in the UI so a reviewer can tell
    # curated/verified data apart from thinner seed entries.
    field_tested: Mapped[bool] = mapped_column(default=False)

    state: Mapped["State"] = relationship(back_populates="waterbodies")
    access_points: Mapped[list["AccessPoint"]] = relationship(
        back_populates="waterbody", cascade="all, delete-orphan"
    )
    species_links: Mapped[list["WaterbodySpecies"]] = relationship(
        back_populates="waterbody", cascade="all, delete-orphan"
    )


class AccessPoint(Base):
    """A confirmed-public entry point. Never inferred — only what a source
    explicitly documents as public. See PRD §12: "地图不会把未经确认的私人
    区域标为公共入口" (acceptance criterion, not a suggestion)."""

    __tablename__ = "access_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    waterbody_id: Mapped[int] = mapped_column(ForeignKey("waterbodies.id"))
    name: Mapped[str] = mapped_column(String(128))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    access_type: Mapped[str] = mapped_column(String(32))  # bank, pier, boat_ramp, park
    public_status: Mapped[str] = mapped_column(String(16), default="confirmed_public")
    parking: Mapped[bool] = mapped_column(default=False)

    waterbody: Mapped["Waterbody"] = relationship(back_populates="access_points")


class Species(Base):
    __tablename__ = "species"

    id: Mapped[int] = mapped_column(primary_key=True)
    common_name: Mapped[str] = mapped_column(String(64), unique=True)
    scientific_name: Mapped[str] = mapped_column(String(128))
    difficulty: Mapped[str] = mapped_column(String(16))  # beginner/intermediate/advanced
    profile: Mapped[str] = mapped_column(Text)  # short habitat/behavior blurb

    waterbody_links: Mapped[list["WaterbodySpecies"]] = relationship(back_populates="species")
    conditions: Mapped[list["SpeciesCondition"]] = relationship(
        back_populates="species", cascade="all, delete-orphan"
    )


class WaterbodySpecies(Base):
    """Confirms a species is actually documented in this lake — never
    assumed from a statewide species list (PRD §4.2)."""

    __tablename__ = "waterbody_species"

    waterbody_id: Mapped[int] = mapped_column(ForeignKey("waterbodies.id"), primary_key=True)
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id"), primary_key=True)
    confidence: Mapped[str] = mapped_column(String(16))  # confirmed/likely/reported
    evidence: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(512))
    observed_at: Mapped[datetime] = mapped_column(DateTime)

    waterbody: Mapped["Waterbody"] = relationship(back_populates="species_links")
    species: Mapped["Species"] = relationship(back_populates="waterbody_links")


class SpeciesCondition(Base):
    """Season/weather/habitat rules used by the scoring engine (Day 2)."""

    __tablename__ = "species_conditions"

    id: Mapped[int] = mapped_column(primary_key=True)
    species_id: Mapped[int] = mapped_column(ForeignKey("species.id"))
    season: Mapped[str] = mapped_column(String(16))
    temperature_range: Mapped[str] = mapped_column(String(32))  # "60-75F"
    weather_preferences: Mapped[str] = mapped_column(Text)
    habitat_rules: Mapped[str] = mapped_column(Text)

    species: Mapped["Species"] = relationship(back_populates="conditions")


class SourceRecord(Base):
    """Every fact worth citing keeps its provenance. This is what makes the
    AI Advisor's "cite your sources" behavior possible instead of aspirational."""

    __tablename__ = "source_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(32))  # tpwd, nws, manual_curation
    url: Mapped[str] = mapped_column(String(512))
    publisher: Mapped[str] = mapped_column(String(128))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
