"""Bait and tackle shops, from OpenStreetMap (data_import/tackle_shops.py).

A place to buy bait or gear near the water: shown on the map, never part of
a lake's facts, its score or the AI advisor. Only what OpenStreetMap's
mappers tagged: a shop is here because someone mapped it as a fishing or
bait shop, not because FishEye guessed from its name.
"""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

KIND_BAIT = "bait"  # sells live or natural bait (and usually tackle)
KIND_TACKLE = "tackle"  # fishing gear; bait not tagged
KIND_STORE = "store"  # a fishing retailer's store (Bass Pro Shops, Cabela's, Academy)


class TackleShop(Base):
    __tablename__ = "tackle_shops"
    __table_args__ = (Index("ix_tackle_shops_lat_lng", "latitude", "longitude"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # "n123" / "w456": the OpenStreetMap element, so a re-import updates the
    # same row and the popup can link to it.
    osm_ref: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(16))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    state_code: Mapped[str] = mapped_column(String(2), index=True)
    address: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    website: Mapped[str | None] = mapped_column(String(300), nullable=True)
    opening_hours: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_record_id: Mapped[int | None] = mapped_column(ForeignKey("source_records.id"), nullable=True)
