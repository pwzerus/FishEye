"""Which water a point is on: a lake on the map or a named river (ADR 0040).

A catch goes on water FishEye can name. The test is distance to the real
shoreline (or river line), not to a lake's centre: within SNAP_M counts,
because anglers stand on the bank, phones' GPS drifts by tens of metres and
a finger on a map is wider than a creek. Inside an outline is distance 0.

The shapes are stored as small encoded pieces (models/water.py), so this
needs no geometry library: the nine grid cells around the point, a few
pieces decoded, flat-earth metres around the point (fine at this range).

A state whose shapes haven't been imported yet (`data_ready`) is not held
to the rule: there, lakes are matched by their box, and a catch away from
any is allowed as before. Lakes with no outline anywhere (a few verified
lakes OpenStreetMap doesn't map) are matched by their box, or within
NO_OUTLINE_RADIUS_M of their centre.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Iterable, Sequence

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.db.spatial import bbox_filter
from app.models.water import CELL_DEG, River, RiverReach, WaterPiece, cell_of
from app.models.waterbody import Waterbody

SNAP_M = 150.0
NO_OUTLINE_RADIUS_M = 300.0
LAKE = "lake"
RIVER = "river"

_M_PER_DEG_LAT = 110_574.0
_M_PER_DEG_LNG = 111_320.0


# ------------------------------------------------------------- encoding


def encode(points: Iterable[tuple[float, float]]) -> str:
    """Google's encoded polyline of (lat, lng) points, at 1e-5 degrees."""
    out: list[str] = []
    plat = plng = 0
    for lat, lng in points:
        ilat, ilng = round(lat * 1e5), round(lng * 1e5)
        for v in (ilat - plat, ilng - plng):
            v = ~(v << 1) if v < 0 else v << 1
            while v >= 0x20:
                out.append(chr((0x20 | (v & 0x1F)) + 63))
                v >>= 5
            out.append(chr(v + 63))
        plat, plng = ilat, ilng
    return "".join(out)


def decode(s: str) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    i = lat = lng = 0
    n = len(s)
    while i < n:
        deltas = []
        for _ in range(2):
            shift = result = 0
            while True:
                b = ord(s[i]) - 63
                i += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            deltas.append(~(result >> 1) if result & 1 else result >> 1)
        lat += deltas[0]
        lng += deltas[1]
        points.append((lat / 1e5, lng / 1e5))
    return points


# ------------------------------------------------------------- distance


def _xy(points: Sequence[tuple[float, float]], lat0: float, lng0: float, kx: float) -> list[tuple[float, float]]:
    return [((lng - lng0) * kx, (lat - lat0) * _M_PER_DEG_LAT) for lat, lng in points]


def _segment_distance(ax: float, ay: float, bx: float, by: float) -> float:
    """From the origin to the segment a-b."""
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / length2))
    return math.hypot(ax + t * dx, ay + t * dy)


def _line_distance(xy: list[tuple[float, float]]) -> float:
    if len(xy) == 1:
        return math.hypot(*xy[0])
    return min(_segment_distance(*xy[i], *xy[i + 1]) for i in range(len(xy) - 1))


def _crossings(xy: list[tuple[float, float]]) -> int:
    """Edges of a ring crossed by a ray from the origin along +x."""
    n = 0
    for i in range(len(xy) - 1):
        (x1, y1), (x2, y2) = xy[i], xy[i + 1]
        if (y1 > 0) != (y2 > 0) and 0 < x1 + (x2 - x1) * (0 - y1) / (y2 - y1):
            n += 1
    return n


def piece_distance(shape: str, geometry: str, lat: float, lng: float) -> float:
    """Metres from the point to the piece: 0 inside an area."""
    kx = _M_PER_DEG_LNG * math.cos(math.radians(lat))
    parts = json.loads(geometry)
    best = math.inf
    if shape == "line":
        for line in parts:
            best = min(best, _line_distance(_xy(decode(line), lat, lng, kx)))
        return best
    for polygon in parts:
        rings = [_xy(decode(ring), lat, lng, kx) for ring in polygon]
        # Inside the outer ring and in no hole: an even-odd count over all
        # of a polygon's rings says exactly that.
        if sum(_crossings(r) for r in rings) % 2 == 1:
            return 0.0
        for r in rings:
            best = min(best, _line_distance(r))
    return best


def _box_distance(lat: float, lng: float, south: float, west: float, north: float, east: float) -> float:
    kx = _M_PER_DEG_LNG * math.cos(math.radians(lat))
    dy = max(south - lat, 0.0, lat - north) * _M_PER_DEG_LAT
    dx = max(west - lng, 0.0, lng - east) * kx
    return math.hypot(dx, dy)


def _centre_distance(lat: float, lng: float, wb: Waterbody) -> float:
    kx = _M_PER_DEG_LNG * math.cos(math.radians(lat))
    return math.hypot((wb.longitude - lng) * kx, (wb.latitude - lat) * _M_PER_DEG_LAT)


# --------------------------------------------------------------- lookup


@dataclass(frozen=True)
class WaterMatch:
    kind: str  # LAKE | RIVER
    id: int
    name: str
    distance_m: float  # 0: on the water


def neighbour_cells(lat: float, lng: float) -> list[int]:
    return [cell_of(lat + dy * CELL_DEG, lng + dx * CELL_DEG) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]


def data_ready(db: Session, state_code: str | None) -> bool:
    """Have this state's shapes been imported? Until they have, the rule
    that a catch is on named water isn't enforced there."""
    if not state_code:
        return False
    return bool(db.scalar(select(exists().where(WaterPiece.state_code == state_code.upper()))))


def _lakes_without_outline(db: Session, lat: float, lng: float, snap_m: float) -> dict[int, float]:
    """Lakes near the point that have no outline, by box or centre."""
    d = 0.25  # the centre of any lake whose box could hold the point
    lakes = db.scalars(select(Waterbody).where(bbox_filter(db, lng - d, lat - d, lng + d, lat + d))).all()
    near: dict[int, float] = {}
    for wb in lakes:
        if wb.bbox_south is not None and wb.bbox_west is not None and wb.bbox_north is not None and wb.bbox_east is not None:
            dist = _box_distance(lat, lng, wb.bbox_south, wb.bbox_west, wb.bbox_north, wb.bbox_east)
        else:
            dist = max(0.0, _centre_distance(lat, lng, wb) - NO_OUTLINE_RADIUS_M)
        if dist <= snap_m:
            near[wb.id] = dist
    if not near:
        return near
    outlined = set(
        db.scalars(select(WaterPiece.waterbody_id).where(WaterPiece.waterbody_id.in_(near)).distinct()).all()
    )
    return {wid: dist for wid, dist in near.items() if wid not in outlined}


def find_water(db: Session, lat: float, lng: float, snap_m: float = SNAP_M) -> WaterMatch | None:
    """The water at this point, or None. Inside an outline beats near one;
    a lake beats a river at the same distance (a river's line often runs
    through the reservoir it feeds); a verified lake beats an OpenStreetMap
    one (the same water mapped twice)."""
    lakes: dict[int, float] = {}
    rivers: dict[int, float] = {}
    rows = db.execute(
        select(WaterPiece.waterbody_id, WaterPiece.river_id, WaterPiece.shape, WaterPiece.geometry)
        .where(WaterPiece.cell.in_(neighbour_cells(lat, lng)))
    ).all()
    for waterbody_id, river_id, shape, geometry in rows:
        found, key = (lakes, waterbody_id) if waterbody_id is not None else (rivers, river_id)
        if key is None or found.get(key) == 0.0:
            continue
        dist = piece_distance(shape, geometry, lat, lng)
        if dist <= snap_m and dist < found.get(key, math.inf):
            found[key] = dist
    for wid, dist in _lakes_without_outline(db, lat, lng, snap_m).items():
        lakes[wid] = min(dist, lakes.get(wid, math.inf))
    if not lakes and not rivers:
        return None

    names: dict[tuple[str, int], tuple[str, bool]] = {}
    if lakes:
        for wid, name, tier in db.execute(
            select(Waterbody.id, Waterbody.name, Waterbody.data_tier).where(Waterbody.id.in_(lakes))
        ):
            names[(LAKE, wid)] = (name, tier == "verified")
    if rivers:
        for rid, name in db.execute(select(River.id, River.name).where(River.id.in_(rivers))):
            names[(RIVER, rid)] = (name, False)
    candidates = [
        (dist, 0 if kind == LAKE else 1, 0 if names[(kind, wid)][1] else 1, kind, wid)
        for kind, found in ((LAKE, lakes), (RIVER, rivers))
        for wid, dist in found.items()
        if (kind, wid) in names
    ]
    if not candidates:
        return None
    dist, _, _, kind, wid = min(candidates)
    return WaterMatch(kind=kind, id=wid, name=names[(kind, wid)][0], distance_m=round(dist, 1))


def reach_point(db: Session, river_id: int, county_geoid: str | None, near: tuple[float, float]) -> tuple[float, float] | None:
    """Where others see a catch on this river (ADR 0038): its point in the
    catch's county, else the river's nearest county point, else the river's
    own label point."""
    reaches = db.scalars(select(RiverReach).where(RiverReach.river_id == river_id)).all()
    for r in reaches:
        if r.county_geoid == county_geoid:
            return r.latitude, r.longitude
    if reaches:
        lat, lng = near
        best = min(reaches, key=lambda r: (r.latitude - lat) ** 2 + ((r.longitude - lng) * math.cos(math.radians(lat))) ** 2)
        return best.latitude, best.longitude
    river = db.get(River, river_id)
    return (river.latitude, river.longitude) if river else None
