"""How near the sea a place is, for the fish photo check (docs/adr/0063).

A catch far from the sea can't be a fish of the sea, so there the check
leaves those fish out (fish_id.Identification.inland): a freshwater drum is
no longer read as a black drum, a channel catfish as a hardhead catfish.

"Near" means a coastal spot (models/coastal_spot.py: piers, jetties, fishing
spots and boat ramps within about a kilometre of the sea's shore) within
INLAND_KM. The spots are on the sea coasts only, not the Great Lakes. Where
they are sparse (parts of Alaska, Louisiana's marshes) a place near the
shore can count as inland; the check there is the one FishEye had before it
knew any fish of the sea.
"""
from __future__ import annotations

import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.coastal_spot import CoastalSpot

# Past this from any coastal spot, rivers and lakes are fresh water. The fish
# of the sea that swim further up are kept everywhere (fish_id_classes.UP_RIVERS).
INLAND_KM = 50.0
_EARTH_KM = 6371.0


def _km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2
    return 2 * _EARTH_KM * math.asin(min(1.0, math.sqrt(a)))


def inland(db: Session, lat: float, lng: float) -> bool:
    """No coastal spot within INLAND_KM. False while no coastal spots are
    imported at all: then nothing is left out."""
    dlat = INLAND_KM / 110.574
    dlng = INLAND_KM / (111.320 * max(math.cos(math.radians(lat)), 0.01))
    near = db.execute(
        select(CoastalSpot.latitude, CoastalSpot.longitude).where(
            CoastalSpot.latitude.between(lat - dlat, lat + dlat),
            CoastalSpot.longitude.between(lng - dlng, lng + dlng),
        )
    ).all()
    if any(_km(lat, lng, a, b) <= INLAND_KM for a, b in near):
        return False
    return db.scalar(select(CoastalSpot.id).limit(1)) is not None
