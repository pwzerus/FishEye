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

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
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
    # "open" | "closed" — whether the *waterbody itself* is currently open
    # to public access at all, independent of any single AccessPoint's own
    # public_status. Added after TPWD's own access page for Gibbons Creek
    # Reservoir stated it has been closed to the public since 12/25/21;
    # PRD §12 says never present unconfirmed/closed access as public, so a
    # closed lake must be distinguishable in the API, not just implied by
    # an empty access_points list (which also happens to mean "no data
    # yet" for a lake nobody has surveyed, a very different situation).
    public_access_status: Mapped[str] = mapped_column(String(16), default="open")
    # "verified" | "osm". How much this app actually knows about the lake,
    # which decides what the UI and every downstream service may do with it:
    #   verified — hand-curated or scraped from an official source (TPWD):
    #              species evidence, confirmed-public access, scoring, AI
    #              explanations all apply.
    #   osm      — imported from OpenStreetMap to show that a lake exists at
    #              all (docs/adr/0010-statewide-osm-layer.md). Community-
    #              mapped, not official: no species are ever attached, its
    #              access points are "osm_reported" (never confirmed_public,
    #              so scoring never ranks them), and the UI says so.
    data_tier: Mapped[str] = mapped_column(String(16), default="verified")
    # OSM element reference ("way/123", "relation/456") — what makes the
    # importer idempotent, and what links a verified lake to its OSM twin so
    # a re-import never creates a duplicate "Lake Somerville" next to ours.
    osm_ref: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    # "lake" | "reservoir" | "pond", from OSM's water=* tag; None for
    # hand-curated rows. Ponds get their own warning in the UI: in Texas
    # many are on private land, and unlike a reservoir there's rarely an
    # official public-access page to check.
    water_type: Mapped[str | None] = mapped_column(String(16), nullable=True)

    state: Mapped["State"] = relationship(back_populates="waterbodies")
    access_points: Mapped[list["AccessPoint"]] = relationship(
        back_populates="waterbody", cascade="all, delete-orphan"
    )
    species_links: Mapped[list["WaterbodySpecies"]] = relationship(
        back_populates="waterbody", cascade="all, delete-orphan"
    )
    occurrences: Mapped[list["SpeciesOccurrence"]] = relationship(
        back_populates="waterbody", cascade="all, delete-orphan"
    )

    # The map's viewport query filters on lat/lng ranges; with a statewide
    # import this table goes from 7 rows to thousands.
    __table_args__ = (Index("ix_waterbodies_lat_lng", "latitude", "longitude"),)


class AccessPoint(Base):
    """An entry point to a waterbody. Never inferred from geography — only
    what a source explicitly documents. See PRD §12: "地图不会把未经确认的
    私人区域标为公共入口" (acceptance criterion, not a suggestion).

    public_status is what keeps sources from blurring together:
      confirmed_public — an official source says so; the only status the
                         scoring engine ranks (services/recommendations.py).
      osm_reported     — OpenStreetMap tags it as a public slipway/pier.
                         Shown to users with a "verify before you go" label,
                         never scored, never described as confirmed."""

    __tablename__ = "access_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    waterbody_id: Mapped[int] = mapped_column(ForeignKey("waterbodies.id"))
    name: Mapped[str] = mapped_column(String(128))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    access_type: Mapped[str] = mapped_column(String(32))  # bank, pier, boat_ramp, park
    public_status: Mapped[str] = mapped_column(String(16), default="confirmed_public")
    parking: Mapped[bool] = mapped_column(default=False)
    osm_ref: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)

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


class SpeciesOccurrence(Base):
    """One outside record of a species at a lake: a GBIF occurrence (museum
    specimen, agency survey record or iNaturalist observation) whose
    coordinates fall inside the lake's extent.

    This is the "reported" evidence tier (docs/adr/0012-gbif-reported-species.md)
    and is deliberately a separate table from WaterbodySpecies:
      - WaterbodySpecies is what an official survey confirms. Scoring and the
        AI advisor read only that.
      - SpeciesOccurrence says a fish *has been recorded* here, at some point,
        by someone. It's shown with its count, latest year and source, and
        never described as confirmed (PRD constraints 1 and 10).

    One row per record, not per species, so the licence stays attached to
    each record: non-commercial records can be excluded later with a setting,
    without re-importing (docs/commercialization.md). `source` leaves room for
    other kinds of report, e.g. future FishEye community photos."""

    __tablename__ = "species_occurrences"

    id: Mapped[int] = mapped_column(primary_key=True)
    waterbody_id: Mapped[int] = mapped_column(ForeignKey("waterbodies.id"), index=True)
    # A species guide's common_name (app/knowledge/species_guides.py). Not a
    # foreign key to Species: that table only holds fish some official
    # source has confirmed somewhere.
    species_name: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(16), default="gbif")
    source_record_id: Mapped[str] = mapped_column(String(64))  # GBIF occurrence key
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    basis_of_record: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Who collected it, grouped for display: "Fishes of Texas", "iNaturalist",
    # "TPWD" or "Other collections". The raw fields are kept as well.
    source_group: Mapped[str] = mapped_column(String(32))
    dataset_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    institution_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # "CC0" | "CC BY" | "CC BY-NC" | "other/unknown"
    license: Mapped[str] = mapped_column(String(16))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    imported_at: Mapped[datetime] = mapped_column(DateTime)

    waterbody: Mapped["Waterbody"] = relationship(back_populates="occurrences")

    __table_args__ = (UniqueConstraint("source", "source_record_id", name="uq_occurrence_source_record"),)


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
