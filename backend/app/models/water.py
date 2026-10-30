"""Where the water is: lake outlines and named rivers (docs/adr/0040).

Until these, a lake was a centre point and a box, and a river was nothing
at all. A catch has to be on water we can name (services/water.py), so the
map needs the shapes, not just the points.

The shapes come from OpenStreetMap through data_import/water_shapes.py,
which cuts every outline and river line into pieces no bigger than one grid
cell (CELL_DEG). That is what lets the API answer "what water is here?"
from an ordinary integer index on any database, with no geometry library
on the server: look in the nine cells around the point, decode a handful of
pieces, measure.
"""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# A piece's box is at most this wide and tall, in degrees (~5.5 km north to
# south). Any point within a few kilometres of a piece is in the cell of the
# piece's centre or one of the eight around it.
CELL_DEG = 0.05


def cell_of(lat: float, lng: float) -> int:
    """The grid cell a point is in, as one integer."""
    return (int(lat // CELL_DEG) + 2000) * 10_000 + (int(lng // CELL_DEG) + 4000)


class River(Base):
    """A named river, stream or canal within one state: the OpenStreetMap
    ways of that name that touch each other (or share a waterway relation),
    joined into one. Two "Mill Creek"s in one state that never meet are two
    rows. A river through two states is a row in each."""

    __tablename__ = "rivers"

    id: Mapped[int] = mapped_column(primary_key=True)
    state_id: Mapped[int] = mapped_column(ForeignKey("states.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    waterway: Mapped[str] = mapped_column(String(16))  # river | stream | canal
    # The waterway relation when there is one, else the river's lowest way:
    # what a re-import matches on to keep the id.
    osm_ref: Mapped[str] = mapped_column(String(32))
    # A point on the river near its middle, for a label.
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    length_km: Mapped[float] = mapped_column(Float)
    source_url: Mapped[str] = mapped_column(String(512))

    reaches: Mapped[list[RiverReach]] = relationship(cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("state_id", "osm_ref", name="uq_rivers_state_ref"),)


class RiverReach(Base):
    """A river within one county, and a point on it there. A catch on a long
    river is shown to others at its reach's point, never its own spot (ADR
    0038), and catches are counted per reach: "Chattahoochee River, Fulton
    County" says where; the Chattahoochee alone is 700 km."""

    __tablename__ = "river_reaches"

    id: Mapped[int] = mapped_column(primary_key=True)
    river_id: Mapped[int] = mapped_column(ForeignKey("rivers.id", ondelete="CASCADE"), index=True)
    county_geoid: Mapped[str] = mapped_column(String(5))
    county_name: Mapped[str] = mapped_column(String(64))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)

    __table_args__ = (UniqueConstraint("river_id", "county_geoid", name="uq_river_reaches_river_county"),)


class WaterPiece(Base):
    """One grid cell's worth of a lake's outline or a river's line (or the
    outline of a wide river's water). Exactly one of waterbody_id and
    river_id is set.

    `geometry` is JSON: for "area", a list of polygons, each a list of rings
    (outer first, then holes); for "line", a list of lines. Every ring and
    line is a Google encoded polyline at 1e-5 degrees (about a metre)."""

    __tablename__ = "water_pieces"

    id: Mapped[int] = mapped_column(primary_key=True)
    # The import that wrote it, so a re-import replaces one state's rows.
    state_code: Mapped[str] = mapped_column(String(2), index=True)
    waterbody_id: Mapped[int | None] = mapped_column(
        ForeignKey("waterbodies.id", ondelete="CASCADE"), nullable=True, index=True
    )
    river_id: Mapped[int | None] = mapped_column(
        ForeignKey("rivers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    shape: Mapped[str] = mapped_column(String(4))  # "area" | "line"
    cell: Mapped[int] = mapped_column(Integer)
    geometry: Mapped[str] = mapped_column(Text)

    __table_args__ = (Index("ix_water_pieces_cell", "cell"),)
