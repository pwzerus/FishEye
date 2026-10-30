"""Lake outlines and named rivers, from the Geofabrik extracts (ADR 0040).

A catch has to be on water FishEye can name (services/water.py). The lake
import (geofabrik_lakes.py) keeps only each lake's box; this adds the shapes:

- every imported lake's outline: all the OpenStreetMap elements the import
  merges into it (osm_waterbody_import.merge_pieces), simplified to a few
  metres;
- every named river, stream and canal: its ways joined where they meet or
  share a waterway relation, simplified, with the outlines of the wide
  river's water it runs through, and its point in each county it crosses
  (where others see a catch on it, ADR 0038);
- an outline for each verified lake that has no OpenStreetMap twin, from
  whatever water OpenStreetMap maps at its centre (often an unnamed pond:
  Georgia's public fishing area lakes).

Everything is cut into pieces no bigger than one grid cell (models/water.py)
and written as encoded polylines, so the import and the API need no
geometry library: this extract needs pyosmium and shapely
(requirements-import.txt), the import only requirements.txt.

Per state, after geofabrik_lakes has written osm_cache/<code>_osm.json:

1. extract  osm_cache/<code>_water.json.gz (needs the state's .osm.pbf);
2. import   replaces the state's pieces and rivers. River ids are kept for
            rivers that are still there, so catches keep their river; the
            state's catches are checked against the new shapes at the next
            startup (services/pins.fill_water).

    python -m app.data_import.water_shapes --states GA
    python -m app.data_import.water_shapes --states all
    # On a server, from copied osm_cache/*_water.json.gz files:
    python -m app.data_import.water_shapes --states all --import-only
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from app.data_import.us_states import BY_CODE, STATES
from app.models.water import CELL_DEG, cell_of
from app.services.water import SNAP_M, encode

EXTRACT_VERSION = 1
PBF_DIR = Path("geofabrik_cache")
OUT_DIR = Path("osm_cache")

# Kinds of named waterway that count as a river, best first: a river whose
# ways are tagged differently along the way takes the best.
RIVER_LINES = {"river": 0, "canal": 1, "stream": 2}
# natural=water + water=<this> (or the old waterway=riverbank): the water of
# a river wide enough to be drawn as an area.
RIVER_AREAS = {"river", "canal", "stream", "rapids"}
# A named stream shorter than this, all its ways joined, is left out: the
# named ditches and trickles, not the creeks anglers fish.
MIN_STREAM_KM = 1.0
LINE_TOLERANCE_DEG = 0.0001  # ~10 m
REACH_STEP_KM = 1.0
# Water (other than a river's) this close to a verified lake's centre may be
# that lake.
ORPHAN_SEARCH_M = SNAP_M


def payload_path(code: str, out_dir: Path = OUT_DIR) -> Path:
    return out_dir / f"{code.lower()}_water.json.gz"


# --------------------------------------------------------------------------
# Geometry helpers (shapely, extract only)
# --------------------------------------------------------------------------


def _km2(geom: Any) -> float:
    lat = (geom.bounds[1] + geom.bounds[3]) / 2
    return geom.area * 111.32 * 110.57 * math.cos(math.radians(lat))


def _lake_tolerance(geom: Any) -> float:
    """A few metres for ponds, more for the big reservoirs, whose detail
    nobody fishing from a boat a kilometre out needs."""
    km2 = _km2(geom)
    metres = 4.0 if km2 < 50 else 12.0 if km2 < 1000 else 30.0
    return metres / 111_320.0


def _polygonal(geom: Any) -> Any | None:
    """The polygons in a geometry, made valid; None if there are none."""
    import shapely
    from shapely.geometry import MultiPolygon, Polygon

    if geom is None or geom.is_empty:
        return None
    if not geom.is_valid:
        geom = shapely.make_valid(geom)
    if isinstance(geom, (Polygon, MultiPolygon)):
        return geom
    polys = [g for g in getattr(geom, "geoms", []) if isinstance(g, (Polygon, MultiPolygon))]
    if not polys:
        return None
    return shapely.union_all(polys)


def _linear(geom: Any) -> list[Any]:
    from shapely.geometry import LineString, MultiLineString

    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, LineString):
        return [geom]
    if isinstance(geom, MultiLineString):
        return list(geom.geoms)
    return [g for part in getattr(geom, "geoms", []) for g in _linear(part)]


def _areas(geom: Any) -> list[Any]:
    from shapely.geometry import MultiPolygon, Polygon

    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    return [g for part in getattr(geom, "geoms", []) for g in _areas(part)]


def subdivide(geom: Any, step: float = CELL_DEG) -> list[Any]:
    """Cut a geometry until every part's box is at most `step` wide and tall.
    Halving the longer side each time keeps the work near-linear even for
    Lake Superior."""
    from shapely.geometry import box

    out: list[Any] = []
    stack = [geom]
    while stack:
        g = stack.pop()
        if g is None or g.is_empty:
            continue
        minx, miny, maxx, maxy = g.bounds
        if maxx - minx <= step and maxy - miny <= step:
            out.append(g)
            continue
        if maxx - minx >= maxy - miny:
            mid = (minx + maxx) / 2
            halves = (box(minx - 1, miny - 1, mid, maxy + 1), box(mid, miny - 1, maxx + 1, maxy + 1))
        else:
            mid = (miny + maxy) / 2
            halves = (box(minx - 1, miny - 1, maxx + 1, mid), box(minx - 1, mid, maxx + 1, maxy + 1))
        stack.extend(g.intersection(h) for h in halves)
    return out


def _lat_lng(coords: Iterable[tuple[float, ...]]) -> list[tuple[float, float]]:
    return [(c[1], c[0]) for c in coords]


def pieces_of(geom: Any, shape: str) -> list[list[Any]]:
    """[cell, shape, parts] rows for one water's area or lines, one per grid
    cell (a part goes to the cell its box's centre is in)."""
    by_cell: dict[int, list[Any]] = defaultdict(list)
    for part in subdivide(geom):
        items = _areas(part) if shape == "area" else _linear(part)
        for g in items:
            minx, miny, maxx, maxy = g.bounds
            cell = cell_of((miny + maxy) / 2, (minx + maxx) / 2)
            if shape == "area":
                if len(g.exterior.coords) < 4:
                    continue
                rings = [g.exterior, *(r for r in g.interiors if len(r.coords) >= 4)]
                by_cell[cell].append([encode(_lat_lng(r.coords)) for r in rings])
            elif len(g.coords) >= 2:
                by_cell[cell].append(encode(_lat_lng(g.coords)))
    return [[cell, shape, parts] for cell, parts in sorted(by_cell.items())]


def _line_km(coords: list[tuple[float, float]]) -> float:
    """Length of a line of (lat, lng) points, in km."""
    from app.services.geo import haversine_km

    return sum(haversine_km(*coords[i], *coords[i + 1]) for i in range(len(coords) - 1))


def _samples(lines: list[list[tuple[float, float]]], step_km: float = REACH_STEP_KM) -> list[tuple[float, float]]:
    """A point every `step_km` along each line, and each line's middle."""
    from app.services.geo import haversine_km

    out: list[tuple[float, float]] = []
    for coords in lines:
        if len(coords) < 2:
            continue
        out.append(coords[len(coords) // 2])
        walked = 0.0
        for i in range(len(coords) - 1):
            walked += haversine_km(*coords[i], *coords[i + 1])
            if walked >= step_km:
                out.append(coords[i + 1])
                walked = 0.0
    return out


def reaches_of(samples: list[tuple[float, float]]) -> tuple[list[list[Any]], tuple[float, float]]:
    """Per county, the sample nearest the middle of the county's samples;
    and the river's label point, the sample nearest the middle of all."""
    from app.services import counties

    def middle(points: list[tuple[float, float]]) -> tuple[float, float]:
        lat = sum(p[0] for p in points) / len(points)
        lng = sum(p[1] for p in points) / len(points)
        return min(points, key=lambda p: (p[0] - lat) ** 2 + (p[1] - lng) ** 2)

    by_county: dict[str, tuple[str, list[tuple[float, float]]]] = {}
    for lat, lng in samples:
        c = counties.county_at(lat, lng)
        if c is not None:
            by_county.setdefault(c.geoid, (c.name, []))[1].append((lat, lng))
    reaches = [
        [geoid, name, *(round(v, 6) for v in middle(points))]
        for geoid, (name, points) in sorted(by_county.items())
    ]
    return reaches, middle(samples)


# --------------------------------------------------------------------------
# Extract
# --------------------------------------------------------------------------


class _Reader:
    """Ways' nodes and nodes' coordinates from one extract, fetched in
    filtered passes (pyosmium) and kept only as long as needed."""

    def __init__(self, pbf: Path) -> None:
        self.pbf = str(pbf)

    def relations(self, flt: Any) -> Iterable[Any]:
        import osmium

        yield from osmium.FileProcessor(self.pbf, osmium.osm.RELATION).with_filter(flt)

    def ways(self, flt: Any) -> Iterable[Any]:
        import osmium

        yield from osmium.FileProcessor(self.pbf, osmium.osm.WAY).with_filter(flt)

    def way_nodes(self, ids: set[int]) -> dict[int, list[int]]:
        from osmium.filter import IdFilter

        if not ids:
            return {}
        return {w.id: [n.ref for n in w.nodes] for w in self.ways(IdFilter(ids))}

    def coords(self, node_ids: set[int]) -> dict[int, tuple[float, float]]:
        """(lng, lat) of each node, shapely's order."""
        import osmium
        from osmium.filter import IdFilter

        if not node_ids:
            return {}
        out: dict[int, tuple[float, float]] = {}
        for node in osmium.FileProcessor(self.pbf, osmium.osm.NODE).with_filter(IdFilter(node_ids)):
            if node.location.valid():
                out[node.id] = (node.location.lon, node.location.lat)
        return out


def _line(nodes: list[int], coords: dict[int, tuple[float, float]]) -> Any | None:
    from shapely.geometry import LineString

    pts = [coords[n] for n in nodes if n in coords]
    return LineString(pts) if len(pts) >= 2 else None


def _closed_polygon(nodes: list[int], coords: dict[int, tuple[float, float]]) -> Any | None:
    from shapely.geometry import Polygon

    if len(nodes) < 4 or nodes[0] != nodes[-1]:
        return None
    pts = [coords[n] for n in nodes if n in coords]
    return _polygonal(Polygon(pts)) if len(pts) >= 4 else None


def _relation_polygon(
    members: list[tuple[int, str]], way_nodes: dict[int, list[int]], coords: dict[int, tuple[float, float]]
) -> Any | None:
    """A multipolygon from its member ways: the outer rings' polygons less
    the inner rings'."""
    import shapely
    from shapely.ops import polygonize

    outer = [g for w, role in members if role != "inner" and w in way_nodes if (g := _line(way_nodes[w], coords))]
    inner = [g for w, role in members if role == "inner" and w in way_nodes if (g := _line(way_nodes[w], coords))]
    if not outer:
        return None
    geom = shapely.union_all(list(polygonize(outer)))
    if inner:
        holes = list(polygonize(inner))
        if holes:
            geom = geom.difference(shapely.union_all(holes))
    return _polygonal(geom)


def _ref_ids(refs: Iterable[str], kind: str) -> set[int]:
    return {int(r.split("/", 1)[1]) for r in refs if r.startswith(kind + "/")}


def _lake_outlines(reader: _Reader, lakes: list[Any]) -> dict[str, list[list[Any]]]:
    """Pieces of each lake's outline, by the lake's osm_ref."""
    import shapely
    from osmium.filter import IdFilter

    refs = {ref for lake in lakes for ref in lake.refs}
    rel_members: dict[int, list[tuple[int, str]]] = {}
    for rel in reader.relations(IdFilter(_ref_ids(refs, "relation"))):
        rel_members[rel.id] = [(m.ref, m.role) for m in rel.members if m.type == "w"]
    way_ids = _ref_ids(refs, "way") | {w for ms in rel_members.values() for w, _ in ms}
    way_nodes = reader.way_nodes(way_ids)
    coords = reader.coords({n for nodes in way_nodes.values() for n in nodes})

    out: dict[str, list[list[Any]]] = {}
    for lake in lakes:
        polys = []
        for ref in lake.refs:
            kind, _, num = ref.partition("/")
            if kind == "way" and int(num) in way_nodes:
                polys.append(_closed_polygon(way_nodes[int(num)], coords))
            elif kind == "relation" and int(num) in rel_members:
                polys.append(_relation_polygon(rel_members[int(num)], way_nodes, coords))
        polys = [p for p in polys if p is not None]
        if not polys:
            continue
        geom = _polygonal(shapely.union_all(polys))
        if geom is None:
            continue
        geom = _polygonal(geom.simplify(_lake_tolerance(geom), preserve_topology=True))
        if geom is not None:
            out[lake.osm_ref] = pieces_of(geom, "area")
    return out


def _is_river_area(tags: Any) -> bool:
    return (tags.get("natural") == "water" and tags.get("water") in RIVER_AREAS) or tags.get("waterway") == "riverbank"


def _rivers(reader: _Reader, code: str, outline: Any) -> list[dict[str, Any]]:
    """Named rivers, streams and canals that touch the state."""
    import shapely
    from osmium.filter import TagFilter
    from shapely.geometry import MultiLineString

    from app.data_import.geofabrik_lakes import in_state

    # Waterway relations join a river's ways across gaps (an unnamed stretch
    # through a reservoir); river-area relations are wide rivers' water.
    waterway_rels: list[tuple[str, str, list[int]]] = []
    area_rels: list[list[tuple[int, str]]] = []
    for rel in reader.relations(TagFilter(("type", "waterway"), ("natural", "water"), ("waterway", "riverbank"))):
        tags = rel.tags
        if tags.get("type") == "waterway" and tags.get("waterway") in RIVER_LINES and tags.get("name", "").strip():
            waterway_rels.append(
                (f"relation/{rel.id}", tags.get("name").strip(), [m.ref for m in rel.members if m.type == "w"])
            )
        elif _is_river_area(tags):
            area_rels.append([(m.ref, m.role) for m in rel.members if m.type == "w"])
    in_relation = {w: i for i, (_, _, ways) in enumerate(waterway_rels) for w in ways}

    lines: dict[int, tuple[str, str, list[int]]] = {}  # way id -> (name, waterway, nodes)
    area_ways: dict[int, list[int]] = {}
    flt = TagFilter(*(("waterway", w) for w in (*RIVER_LINES, "riverbank")), ("natural", "water"))
    for way in reader.ways(flt):
        tags = way.tags
        kind = tags.get("waterway")
        if kind in RIVER_LINES:
            name = tags.get("name", "").strip()
            rel = in_relation.get(way.id)
            if rel is not None and (not name or name == waterway_rels[rel][1]):
                name = waterway_rels[rel][1]
            if not name or (kind == "stream" and tags.get("intermittent") == "yes" and rel is None):
                continue
            lines[way.id] = (name, kind, [n.ref for n in way.nodes])
        elif _is_river_area(tags):
            area_ways[way.id] = [n.ref for n in way.nodes]
    member_ids = {w for ms in area_rels for w, _ in ms} - area_ways.keys()
    area_ways.update(reader.way_nodes(member_ids))
    coords = reader.coords({n for _, _, nodes in lines.values() for n in nodes})

    # Ways of one river: same name, and sharing an end, or one relation.
    ids = list(lines)
    parent = {w: w for w in ids}

    def find(w: int) -> int:
        while parent[w] != w:
            parent[w] = parent[parent[w]]
            w = parent[w]
        return w

    ends: dict[tuple[str, int], int] = {}
    for w in ids:
        name, _, nodes = lines[w]
        for n in (nodes[0], nodes[-1]):
            other = ends.setdefault((name, n), w)
            if other != w:
                parent[find(w)] = find(other)
        rel = in_relation.get(w)
        if rel is not None and name == waterway_rels[rel][1]:
            first = next((x for x in waterway_rels[rel][2] if x in lines and lines[x][0] == name), w)
            parent[find(w)] = find(first)
    groups: dict[int, list[int]] = defaultdict(list)
    for w in ids:
        groups[find(w)].append(w)

    rivers: list[dict[str, Any]] = []
    used_refs: set[str] = set()
    for members in groups.values():
        name = lines[members[0]][0]
        kind = min((lines[w][1] for w in members), key=RIVER_LINES.__getitem__)
        geoms = []
        for w in members:
            g = _line(lines[w][2], coords)
            if g is None:
                continue
            minx, miny, maxx, maxy = g.bounds
            if in_state(outline, miny, minx, maxy, maxx, code=code):
                geoms.append(g)
        if not geoms:
            continue
        simplified = [g.simplify(LINE_TOLERANCE_DEG, preserve_topology=False) for g in geoms]
        latlng = [_lat_lng(g.coords) for g in simplified]
        km = sum(_line_km(c) for c in latlng)
        if kind == "stream" and km < MIN_STREAM_KM:
            continue
        # The relation, when its own name is this river's; one relation can
        # hold ways of other names that are other rivers here.
        rel_ref = next(
            (waterway_rels[in_relation[w]][0] for w in members
             if w in in_relation and waterway_rels[in_relation[w]][1] == name),
            None,
        )
        ref = rel_ref if rel_ref and rel_ref not in used_refs else f"way/{min(members)}"
        used_refs.add(ref)
        reaches, label = reaches_of(_samples(latlng))
        rivers.append({
            "ref": ref,
            "name": name,
            "waterway": kind,
            "lat": round(label[0], 6),
            "lng": round(label[1], 6),
            "length_km": round(km, 2),
            "reaches": reaches,
            "_lines": MultiLineString(simplified),
        })
    del coords

    # The water of wide rivers, given to the river whose line runs through
    # it furthest. Water no named line crosses is left out.
    area_coords = reader.coords({n for nodes in area_ways.values() for n in nodes})
    areas = [p for nodes in area_ways.values() if (p := _closed_polygon(nodes, area_coords))]
    areas += [p for ms in area_rels if (p := _relation_polygon(ms, area_ways, area_coords))]
    del area_coords
    by_river: dict[int, list[Any]] = defaultdict(list)
    if rivers and areas:
        tree = shapely.STRtree([r["_lines"] for r in rivers])
        for area in areas:
            hits = tree.query(area, predicate="intersects")
            if len(hits):
                best = max(hits, key=lambda i: area.intersection(rivers[i]["_lines"]).length)
                by_river[int(best)].append(area)
    for i, r in enumerate(rivers):
        r["pieces"] = pieces_of(r.pop("_lines"), "line")
        if by_river.get(i):
            water = _polygonal(shapely.union_all(by_river[i]))
            if water is not None:
                water = _polygonal(water.simplify(LINE_TOLERANCE_DEG / 2, preserve_topology=True))
                r["pieces"] += pieces_of(water, "area")
    return rivers


def orphan_key(lat: float, lng: float) -> str:
    return f"@{lat:.5f},{lng:.5f}"


def _orphan_outlines(reader: _Reader, points: list[tuple[float, float]]) -> dict[str, list[list[Any]]]:
    """For each verified lake with no OpenStreetMap twin, the mapped water
    (named or not, not a river) at or nearest its centre within
    ORPHAN_SEARCH_M. One pass over every node finds what is near them."""
    import osmium
    from osmium.filter import TagFilter
    from shapely.geometry import Point

    if not points:
        return {}
    near_cells = {
        (math.floor(lat * 100) + dy, math.floor(lng * 100) + dx)
        for lat, lng in points for dy in (-2, -1, 0, 1, 2) for dx in (-2, -1, 0, 1, 2)
    }
    near: set[int] = set()
    for node in osmium.FileProcessor(reader.pbf, osmium.osm.NODE):
        loc = node.location
        if loc.valid() and (math.floor(loc.lat * 100), math.floor(loc.lon * 100)) in near_cells:
            near.add(node.id)
    ways: dict[int, list[int]] = {}
    for way in reader.ways(TagFilter(("natural", "water"), ("landuse", "reservoir"))):
        if not _is_river_area(way.tags):
            nodes = [n.ref for n in way.nodes]
            if any(n in near for n in nodes):
                ways[way.id] = nodes
    rels: list[list[tuple[int, str]]] = []
    for rel in reader.relations(TagFilter(("natural", "water"), ("landuse", "reservoir"))):
        members = [(m.ref, m.role) for m in rel.members if m.type == "w"]
        if not _is_river_area(rel.tags) and any(w in ways for w, _ in members):
            rels.append(members)
    member_nodes = reader.way_nodes({w for ms in rels for w, _ in ms} - ways.keys())
    all_ways = {**ways, **member_nodes}
    coords = reader.coords({n for nodes in all_ways.values() for n in nodes})
    polys = [p for nodes in ways.values() if (p := _closed_polygon(nodes, coords))]
    polys += [p for ms in rels if (p := _relation_polygon(ms, all_ways, coords))]

    out: dict[str, list[list[Any]]] = {}
    for lat, lng in points:
        pt = Point(lng, lat)
        inside = [p for p in polys if p.contains(pt)]
        if inside:
            best = min(inside, key=lambda p: p.area)
        else:
            kx = 111_320.0 * math.cos(math.radians(lat))
            close = [(p.distance(pt) * kx, p) for p in polys]
            close = [(d, p) for d, p in close if d <= ORPHAN_SEARCH_M]
            if not close:
                continue
            best = min(close, key=lambda dp: dp[0])[1]
        geom = _polygonal(best.simplify(_lake_tolerance(best), preserve_topology=True))
        if geom is not None:
            out[orphan_key(lat, lng)] = pieces_of(geom, "area")
    return out


def extract(pbf: Path, code: str, lakes_payload: dict[str, Any], orphans: list[tuple[float, float]] = ()) -> dict[str, Any]:
    """The water payload for one state: lake outlines by osm_ref, verified
    lakes' outlines by orphan_key, and rivers."""
    from app.data_import import osm_waterbody_import as osm
    from app.data_import.geofabrik_lakes import DOWNLOAD_BASE, load_outline

    elements, _, _ = osm.parse_elements(lakes_payload)
    lakes = osm.merge_pieces(elements)
    reader = _Reader(pbf)
    t = time.monotonic()
    lake_pieces = _lake_outlines(reader, lakes)
    t_lakes = time.monotonic() - t
    t = time.monotonic()
    rivers = _rivers(reader, code, load_outline(code))
    t_rivers = time.monotonic() - t
    t = time.monotonic()
    orphan_pieces = _orphan_outlines(reader, list(orphans))
    t_orphans = time.monotonic() - t
    return {
        "generator": "FishEye water_shapes (pyosmium, shapely)",
        "extract_version": EXTRACT_VERSION,
        "source": f"{DOWNLOAD_BASE}/{BY_CODE[code].geofabrik}-latest.osm.pbf",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "seconds": {"lakes": round(t_lakes), "rivers": round(t_rivers), "orphans": round(t_orphans)},
        "lakes": lake_pieces,
        "orphans": orphan_pieces,
        "rivers": rivers,
    }


def write_payload(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"))
    os.replace(tmp, path)


def read_payload(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# Import (no geometry library)
# --------------------------------------------------------------------------


def import_payload(db: Any, code: str, payload: dict[str, Any]) -> dict[str, int]:
    """Replace one state's pieces and rivers. Counts of what was written."""
    from sqlalchemy import delete, insert, select, update

    from app.models.community import CatchPin
    from app.models.water import River, RiverReach, WaterPiece
    from app.models.waterbody import State, Waterbody

    state = db.scalar(select(State).where(State.code == code))
    if state is None:
        raise ValueError(f"{code}: no such state in the database; import its lakes first")
    db.execute(delete(WaterPiece).where(WaterPiece.state_code == code))

    def rows_for(pieces: list[list[Any]], **owner: int | None) -> list[dict[str, Any]]:
        return [
            {"state_code": code, "waterbody_id": owner.get("waterbody_id"), "river_id": owner.get("river_id"),
             "shape": shape, "cell": cell, "geometry": json.dumps(parts, separators=(",", ":"))}
            for cell, shape, parts in pieces
        ]

    counts = {"lakes": 0, "lakes_unmatched": 0, "verified_outlines": 0, "rivers": 0, "pieces": 0}
    rows: list[dict[str, Any]] = []
    refs = list(payload.get("lakes", {}))
    by_ref: dict[str, int] = {}
    for i in range(0, len(refs), 500):
        chunk = refs[i : i + 500]
        by_ref.update({ref: wid for wid, ref in db.execute(
            select(Waterbody.id, Waterbody.osm_ref).where(Waterbody.osm_ref.in_(chunk))
        )})
    for ref, pieces in payload.get("lakes", {}).items():
        if ref in by_ref:
            rows += rows_for(pieces, waterbody_id=by_ref[ref])
            counts["lakes"] += 1
        else:
            counts["lakes_unmatched"] += 1
    orphans = {
        orphan_key(lat, lng): wid
        for wid, lat, lng in db.execute(
            select(Waterbody.id, Waterbody.latitude, Waterbody.longitude).where(
                Waterbody.state_id == state.id, Waterbody.data_tier == "verified", Waterbody.osm_ref.is_(None)
            )
        )
    }
    for key, pieces in payload.get("orphans", {}).items():
        if key in orphans:
            rows += rows_for(pieces, waterbody_id=orphans[key])
            counts["verified_outlines"] += 1

    existing = {r.osm_ref: r for r in db.scalars(select(River).where(River.state_id == state.id))}
    kept: list[tuple[River, dict[str, Any]]] = []
    for r in payload.get("rivers", []):
        river = existing.pop(r["ref"], None)
        if river is None:
            river = River(state_id=state.id, osm_ref=r["ref"])
            db.add(river)
        river.name, river.waterway = r["name"][:128], r["waterway"]
        river.latitude, river.longitude, river.length_km = r["lat"], r["lng"], r["length_km"]
        river.source_url = f"https://www.openstreetmap.org/{r['ref']}"
        kept.append((river, r))
    for gone in existing.values():
        db.delete(gone)
    db.flush()
    river_ids = [river.id for river, _ in kept]
    for i in range(0, len(river_ids), 500):
        db.execute(delete(RiverReach).where(RiverReach.river_id.in_(river_ids[i : i + 500])))
    reach_rows = [
        {"river_id": river.id, "county_geoid": geoid, "county_name": name[:64], "latitude": lat, "longitude": lng}
        for river, r in kept for geoid, name, lat, lng in r.get("reaches", [])
    ]
    for river, r in kept:
        rows += rows_for(r.get("pieces", []), river_id=river.id)
    for i in range(0, len(reach_rows), 5000):
        db.execute(insert(RiverReach), reach_rows[i : i + 5000])
    for i in range(0, len(rows), 5000):
        db.execute(insert(WaterPiece), rows[i : i + 5000])
    # The state's catches are checked against the new shapes at startup.
    db.execute(update(CatchPin).where(CatchPin.state_code == code).values(water_distance_m=None))
    counts["rivers"], counts["pieces"] = len(kept), len(rows)
    return counts


# --------------------------------------------------------------------------
# Run
# --------------------------------------------------------------------------


def _orphan_points(db: Any, code: str) -> list[tuple[float, float]]:
    from sqlalchemy import select

    from app.models.waterbody import State, Waterbody

    return [
        (lat, lng)
        for lat, lng in db.execute(
            select(Waterbody.latitude, Waterbody.longitude).join(State, State.id == Waterbody.state_id).where(
                State.code == code, Waterbody.data_tier == "verified", Waterbody.osm_ref.is_(None)
            )
        )
    ]


def main(argv: list[str] | None = None) -> int:
    from app.data_import.geofabrik_lakes import _progress, _save_progress, download, load_or_extract
    from app.db.session import SessionLocal, engine
    from app.db.upgrades import prepare_database

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--states", default="", help="comma-separated codes, or 'all'")
    ap.add_argument("--pbf-dir", type=Path, default=PBF_DIR)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--import-only", action="store_true", help="import existing <code>_water.json.gz payloads")
    ap.add_argument("--extract-only", action="store_true", help="write payloads; leave the database alone")
    ap.add_argument("--force", action="store_true", help="redo states already marked done")
    args = ap.parse_args(argv)

    codes = [s.code for s in STATES] if args.states.lower() == "all" else [c.strip().upper() for c in args.states.split(",") if c.strip()]
    unknown = [c for c in codes if c not in BY_CODE]
    if unknown or not codes:
        print(f"give --states (unknown: {', '.join(unknown)})" if unknown else "give --states", file=sys.stderr)
        return 2

    prepare_database(engine)
    progress_dir = args.out_dir / "water"
    progress_dir.mkdir(parents=True, exist_ok=True)
    progress = _progress(progress_dir)
    for code in codes:
        if progress.get(code, {}).get("imported") and not args.force:
            print(f"{code}: done earlier, skipped")
            continue
        path = payload_path(code, args.out_dir)
        t = time.monotonic()
        if not args.import_only and (args.force or not path.exists()):
            pbf = download(code, args.pbf_dir)
            lakes_payload, _ = load_or_extract(code, pbf, args.out_dir)
            with SessionLocal() as db:
                orphans = _orphan_points(db, code)
            write_payload(path, extract(pbf, code, lakes_payload, orphans))
        if not path.exists():
            print(f"{code}: no {path}; extract it first", file=sys.stderr)
            continue
        entry = {"extracted_at": datetime.now(timezone.utc).isoformat(), "extract_s": round(time.monotonic() - t),
                 "payload_mb": round(path.stat().st_size / 1e6, 1)}
        if not args.extract_only:
            t = time.monotonic()
            with SessionLocal() as db:
                counts = import_payload(db, code, read_payload(path))
                db.commit()
            entry.update(counts, imported=True, import_s=round(time.monotonic() - t))
        progress[code] = {**progress.get(code, {}), **entry}
        _save_progress(progress_dir, progress)
        print(f"{code}: {json.dumps(entry)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
