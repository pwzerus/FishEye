"""Saltwater fishing spots on the coast: piers, jetties, mapped fishing spots
and boat ramps, from OpenStreetMap (data_import/coastal_spots.py) and, in
California, CDFW's list of public piers (data_import/cdfw_piers.py).

The coast has no lakes to put on the map, so these are the places an angler
can walk to (2026-11-18, the owner). Only what the sources list; private
ones are left out at import. Shown on the map, never scored.
"""
from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

KINDS = ("pier", "jetty", "fishing_spot", "boat_ramp")
COASTS = ("atlantic", "gulf", "pacific", "alaska", "hawaii")
SOURCES = ("osm", "cdfw")
# Where next to a California public pier a license is needed again (CDFW's notes).
LICENSE_NOTES = ("shore_wall", "shore_wall_and_inner_jetty", "breakwater", "footbridge")


class CoastalSpot(Base):
    __tablename__ = "coastal_spots"
    __table_args__ = (Index("ix_coastal_spots_lat_lng", "latitude", "longitude"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # The record it came from, so a re-import updates the same row: "n123",
    # "w456" or "r789" for an OpenStreetMap element, "cdfw:<pier>" for one
    # of CDFW's public piers.
    ref: Mapped[str] = mapped_column(String(80), unique=True)
    source: Mapped[str] = mapped_column(String(12), default="osm")
    # The OpenStreetMap element when the spot is mapped there (its own, or
    # the one a CDFW pier was matched to): the popup links to it.
    osm_ref: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    kind: Mapped[str] = mapped_column(String(16))
    coast: Mapped[str] = mapped_column(String(12))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    state_code: Mapped[str] = mapped_column(String(2), index=True)
    # Mapped or listed as a place to fish (OSM fishing=yes|designated or
    # leisure=fishing, or on an agency's list of fishing piers).
    fishing_tagged: Mapped[bool] = mapped_column(Boolean, default=False)
    fee: Mapped[str | None] = mapped_column(String(40), nullable=True)
    opening_hours: Mapped[str | None] = mapped_column(String(120), nullable=True)
    lit: Mapped[bool] = mapped_column(Boolean, default=False)
    operator: Mapped[str | None] = mapped_column(String(120), nullable=True)
    website: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # A California public pier (14 CCR 1.88): no fishing license needed on it.
    no_license: Mapped[bool] = mapped_column(Boolean, default=False)
    license_note: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_record_id: Mapped[int | None] = mapped_column(ForeignKey("source_records.id"), nullable=True)
