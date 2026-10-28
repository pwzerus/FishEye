"""Every state's lakes, from Geofabrik's OpenStreetMap extracts, offline.

docs/adr/0035-lakes-in-every-state.md. The statewide OSM import
(osm_waterbody_import.py) was written against the public Overpass API, one
large query per state. That is fine for one state now and then and wrong
for fifty: Overpass is a shared service and the data-sourcing rules say
bulk data comes from a bulk download. Geofabrik publishes a daily extract
per state (https://download.geofabrik.de/north-america/us/, ODbL).

Per state, three resumable steps:

1. download  geofabrik_cache/<state>-latest.osm.pbf, once (one file at a
             time, resumed if cut off; a ".done" file marks it complete);
2. extract   osm_cache/<code>_osm.json: the same named lakes, reservoirs and
             ponds, and the same slipways, fishing spots and fishing piers
             the Overpass query asks for, as an Overpass-shaped payload
             ("bounds" for water, "center" for access ways), read with
             pyosmium in five filtered passes. Water outside the state (the
             extracts carry a border buffer) is dropped using the Census
             state outlines the map draws (frontend/public/geo/us-states.json).
             Since EXTRACT_VERSION 2 the payload also carries named water
             with no water=* tag; the import decides which of it is a lake
             (untyped_water.judge, docs/adr/0036). A payload from an older
             version is extracted again;
3. import    osm_waterbody_import.run on that payload: the same private-water
             rules, likely_private marks, merging and verified-lake twins.

osm_cache/progress.json records each finished state, so an interrupted run
picks up where it stopped. The payloads are what a server needs: copy them
up and run `osm_waterbody_import --state XX --from-file XX_osm.json` there,
with no download or pyosmium.

    python -m app.data_import.geofabrik_lakes --states all
    python -m app.data_import.geofabrik_lakes --states TX,GA,CA --force
    python -m app.data_import.geofabrik_lakes --report
    # What the untyped-water rules would add, per state, with samples; no
    # database is opened (docs/skills/fisheye-osm-lakes):
    python -m app.data_import.geofabrik_lakes --count-untyped --states all --out-dir untyped_check
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from app.data_import import untyped_water
from app.data_import.provenance import USER_AGENT
from app.data_import.us_states import BY_CODE, STATES, ensure_states

DOWNLOAD_BASE = "https://download.geofabrik.de/north-america/us"
PBF_DIR = Path("geofabrik_cache")
OUT_DIR = Path("osm_cache")
STATE_OUTLINES = Path(__file__).resolve().parents[3] / "frontend" / "public" / "geo" / "us-states.json"
# The outlines are rounded to ~1 km and drawn at 1:10M: a lake on the shore
# or a small island may fall just outside. Anything within this of the
# state counts.
STATE_MARGIN_M = 2000.0

WATER_TYPES = {"lake", "reservoir", "pond"}
# Bumped when extract() starts taking different elements; a cached payload
# from another version is extracted again. 2: named water with no water=* tag.
# 3: such water named after a facility carries "facilities_near"; 4: and
# "places_near"; 5: places are settlements within 20 km.
EXTRACT_VERSION = 5


# --------------------------------------------------------------------------
# State outlines
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Outline:
    rings: tuple[tuple[tuple[float, float], ...], ...]  # (lng, lat); Alaska's west of -180
    bbox: tuple[float, float, float, float]  # west, south, east, north


def load_outline(code: str, path: Path = STATE_OUTLINES) -> Outline:
    data = json.loads(path.read_text(encoding="utf-8"))
    feat = next(f for f in data["features"] if f["properties"]["code"] == code)
    g = feat["geometry"]
    polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    rings = tuple(tuple((float(x), float(y)) for x, y in ring) for poly in polys for ring in poly)
    xs = [p[0] for r in rings for p in r]
    ys = [p[1] for r in rings for p in r]
    return Outline(rings, (min(xs), min(ys), max(xs), max(ys)))


def _inside(outline: Outline, lng: float, lat: float) -> bool:
    inside = False
    for ring in outline.rings:
        j = len(ring) - 1
        for i in range(len(ring)):
            xi, yi = ring[i]
            xj, yj = ring[j]
            if (yi > lat) != (yj > lat) and lng < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
    return inside


def in_state(outline: Outline, south: float, west: float, north: float, east: float, code: str) -> bool:
    """Does this box, widened by STATE_MARGIN_M, touch the state? True when
    a corner or the centre of the box is inside, or a vertex of the outline
    is inside the box. Longitudes east of the date line are shifted by -360
    for Alaska, as its outline is."""
    if code == "AK":
        west = west - 360 if west > 0 else west
        east = east - 360 if east > 0 else east
    dlat = STATE_MARGIN_M / 111_320.0
    dlng = STATE_MARGIN_M / (111_320.0 * max(math.cos(math.radians((south + north) / 2)), 0.01))
    s, w, n, e = south - dlat, west - dlng, north + dlat, east + dlng
    ow, os_, oe, on = outline.bbox
    if e < ow or w > oe or n < os_ or s > on:
        return False
    points = ((w, s), (w, n), (e, s), (e, n), ((w + e) / 2, (s + n) / 2))
    if any(_inside(outline, x, y) for x, y in points):
        return True
    return any(w <= x <= e and s <= y <= n for ring in outline.rings for x, y in ring)


# --------------------------------------------------------------------------
# Download
# --------------------------------------------------------------------------


def download(code: str, pbf_dir: Path = PBF_DIR) -> Path:
    """The state's extract, fetched once and resumed if interrupted."""
    import httpx

    s = BY_CODE[code]
    path = pbf_dir / f"{s.geofabrik}-latest.osm.pbf"
    done = path.with_name(path.name + ".done")
    if done.exists():
        return path
    pbf_dir.mkdir(parents=True, exist_ok=True)
    url = f"{DOWNLOAD_BASE}/{s.geofabrik}-latest.osm.pbf"
    for attempt in range(6):
        have = path.stat().st_size if path.exists() else 0
        headers = {"User-Agent": USER_AGENT, **({"Range": f"bytes={have}-"} if have else {})}
        try:
            with httpx.stream("GET", url, headers=headers, timeout=120, follow_redirects=True) as resp:
                if resp.status_code == 416:  # already complete
                    break
                resp.raise_for_status()
                mode = "ab" if have and resp.status_code == 206 else "wb"
                with path.open(mode) as fh:
                    for chunk in resp.iter_bytes(1 << 20):
                        fh.write(chunk)
            break
        except (httpx.HTTPError, OSError) as exc:
            print(f"  {code}: download interrupted ({exc}); retrying", file=sys.stderr)
            time.sleep(15 * (attempt + 1))
    else:
        raise RuntimeError(f"{code}: could not download {url}")
    done.touch()
    return path


# --------------------------------------------------------------------------
# Extract
# --------------------------------------------------------------------------


def _is_lake(tags: dict[str, str]) -> bool:
    if not tags.get("name", "").strip():
        return False
    if tags.get("landuse") == "reservoir":
        return True
    if tags.get("natural") != "water":
        return False
    # No water=* tag: carried along, and judged by the import (untyped_water).
    return tags.get("water") in WATER_TYPES or not tags.get("water", "").strip()


def _is_untyped(tags: dict[str, str]) -> bool:
    return tags.get("natural") == "water" and tags.get("landuse") != "reservoir" and not tags.get("water", "").strip()


def _is_access(tags: dict[str, str]) -> bool:
    if tags.get("leisure") in ("slipway", "fishing"):
        return True
    return tags.get("man_made") == "pier" and tags.get("fishing") in ("yes", "designated")


def _sample(refs: list[int], n: int = 8) -> list[int]:
    """A few of a facility way's nodes, enough for its rough extent."""
    if len(refs) <= n + 1:
        return refs
    return [*refs[:: len(refs) // n], refs[-1]]


Box = tuple[float, float, float, float]  # south, west, north, east


class FacilityIndex:
    """Mapped facilities by kind, on a coarse grid, for "is a school mapped
    near this pond?" (untyped_water.FACILITY_NEAR_M)."""

    CELL = 0.05  # degrees, ~5 km
    MAX_CELLS = 400  # a box over more cells (a whole town's landuse) goes on a short list

    def __init__(self) -> None:
        self.cells: dict[tuple[int, int], list[tuple[frozenset[str], Box]]] = {}
        self.large: list[tuple[frozenset[str], Box]] = []

    def _span(self, b: Box) -> tuple[range, range]:
        return (range(math.floor(b[0] / self.CELL), math.floor(b[2] / self.CELL) + 1),
                range(math.floor(b[1] / self.CELL), math.floor(b[3] / self.CELL) + 1))

    def add(self, kinds: set[str], b: Box) -> None:
        item = (frozenset(kinds), b)
        rows, cols = self._span(b)
        if len(rows) * len(cols) > self.MAX_CELLS:
            self.large.append(item)
            return
        for r in rows:
            for c in cols:
                self.cells.setdefault((r, c), []).append(item)

    def near(self, b: Box, kinds: set[str], margin_m: float) -> set[str]:
        dlat = margin_m / 111_320.0
        dlng = margin_m / (111_320.0 * max(math.cos(math.radians((b[0] + b[2]) / 2)), 0.01))
        s, w, n, e = b[0] - dlat, b[1] - dlng, b[2] + dlat, b[3] + dlng
        rows, cols = self._span((s, w, n, e))
        found: set[str] = set()
        candidates = [item for r in rows for c in cols for item in self.cells.get((r, c), ())]
        for fk, fb in candidates + self.large:
            if fk & kinds and not (fb[0] > n or fb[2] < s or fb[1] > e or fb[3] < w):
                found |= fk & kinds
        return found


def extract(pbf: Path, code: str, outline: Outline | None = None) -> dict[str, Any]:
    """Overpass-shaped payload for one state's extract."""
    import osmium
    from osmium.filter import IdFilter, KeyFilter, TagFilter

    outline = outline or load_outline(code)
    lake_tags = TagFilter(("natural", "water"), ("landuse", "reservoir"))
    access_tags = TagFilter(("leisure", "slipway"), ("leisure", "fishing"), ("man_made", "pier"))

    # 1. Named water relations, and the ways they are made of.
    relations: dict[int, tuple[dict[str, str], list[int]]] = {}
    for rel in osmium.FileProcessor(str(pbf), osmium.osm.RELATION).with_filter(KeyFilter("name")):
        tags = dict(rel.tags)
        if _is_lake(tags):
            relations[rel.id] = (tags, [m.ref for m in rel.members if m.type == "w"])
    member_ways = {w for _, ws in relations.values() for w in ws}

    # 2. Named water ways and access ways (their own tags), then the member ways.
    ways: dict[int, tuple[dict[str, str] | None, list[int]]] = {}
    for way in osmium.FileProcessor(str(pbf), osmium.osm.WAY).with_filter(lake_tags):
        tags = dict(way.tags)
        if _is_lake(tags):
            ways[way.id] = (tags, [n.ref for n in way.nodes])
    for way in osmium.FileProcessor(str(pbf), osmium.osm.WAY).with_filter(access_tags):
        tags = dict(way.tags)
        if _is_access(tags):
            ways[way.id] = (tags, [n.ref for n in way.nodes])
    missing = member_ways - ways.keys()
    if missing:
        for way in osmium.FileProcessor(str(pbf), osmium.osm.WAY).with_filter(IdFilter(missing)):
            ways[way.id] = (None, [n.ref for n in way.nodes])

    # 2b. Facilities of the kinds untyped water is named after ("Salisbury
    # School Pond": schools), so the import can tell a pond at a school from
    # a "School Lake" that is only a place name (untyped_water.judge).
    wanted: set[str] = set()
    for tags, _ in [*relations.values(), *ways.values()]:
        if tags is not None and _is_lake(tags) and _is_untyped(tags):
            wanted |= untyped_water.named_facilities(tags["name"])
    fac_ways: dict[int, tuple[set[str], list[int]]] = {}
    fac_rels: list[tuple[set[str], list[int]]] = []
    fac_points: list[tuple[set[str], float, float]] = []
    places: list[tuple[str, float, float]] = []
    if wanted:
        specs = [spec for kind in sorted(wanted) for spec in untyped_water.FACILITY_TAGS[kind]]
        pairs = sorted({(k, v) for k, v in specs if v is not None})
        keys = sorted({k for k, v in specs if v is None})
        filters = ([TagFilter(*pairs)] if pairs else []) + ([KeyFilter(*keys)] if keys else [])
        seen_rels: set[int] = set()
        everything = osmium.osm.NODE | osmium.osm.WAY | osmium.osm.RELATION
        for flt in filters:
            for obj in osmium.FileProcessor(str(pbf), everything).with_filter(flt):
                kinds = untyped_water.facility_kinds(dict(obj.tags)) & wanted
                if not kinds:
                    continue
                if isinstance(obj, osmium.osm.Node):
                    if obj.location.valid():
                        fac_points.append((kinds, obj.location.lat, obj.location.lon))
                elif isinstance(obj, osmium.osm.Way):
                    fac_ways.setdefault(obj.id, (kinds, _sample([n.ref for n in obj.nodes])))
                elif obj.id not in seen_rels:
                    seen_rels.add(obj.id)
                    fac_rels.append((kinds, [m.ref for m in obj.members if m.type == "w"][:50]))
        rel_member_ids = {w for _, ws in fac_rels for w in ws} - fac_ways.keys() - ways.keys()
        if rel_member_ids:
            for way in osmium.FileProcessor(str(pbf), osmium.osm.WAY).with_filter(IdFilter(rel_member_ids)):
                fac_ways[way.id] = (set(), _sample([n.ref for n in way.nodes]))
        # Places whose name is in such a water's name: the town of Ball Club,
        # Minnesota, makes "Ball Club Lake" a place name.
        name_words = {
            w for tags, _ in [*relations.values(), *ways.values()]
            if tags is not None and _is_lake(tags) and _is_untyped(tags) and untyped_water.named_facilities(tags["name"])
            for w in untyped_water.name_words(tags["name"])
        }
        place_filter = TagFilter(*(("place", v) for v in untyped_water.PLACE_VALUES))
        for node in osmium.FileProcessor(str(pbf), osmium.osm.NODE).with_filter(place_filter):
            place = node.tags.get("name", "").strip()
            if place and node.location.valid() and set(untyped_water.name_words(place)) <= name_words:
                places.append((place, node.location.lat, node.location.lon))

    # 3. Coordinates of every node those ways use; tagged access nodes.
    needed = {n for _, nodes in ways.values() for n in nodes} | {n for _, refs in fac_ways.values() for n in refs}
    coords: dict[int, tuple[float, float]] = {}
    for node in osmium.FileProcessor(str(pbf), osmium.osm.NODE).with_filter(IdFilter(needed)):
        if node.location.valid():
            coords[node.id] = (node.location.lat, node.location.lon)
    elements: list[dict[str, Any]] = []
    for node in osmium.FileProcessor(str(pbf), osmium.osm.NODE).with_filter(access_tags):
        tags = dict(node.tags)
        if _is_access(tags) and node.location.valid():
            elements.append({"type": "node", "id": node.id, "lat": node.location.lat, "lon": node.location.lon, "tags": tags})

    def box(node_ids: list[int]) -> tuple[float, float, float, float] | None:
        pts = [coords[n] for n in node_ids if n in coords]
        if not pts:
            return None
        lats, lngs = [p[0] for p in pts], [p[1] for p in pts]
        return min(lats), min(lngs), max(lats), max(lngs)

    def bounds(b: tuple[float, float, float, float]) -> dict[str, float]:
        return {"minlat": b[0], "minlon": b[1], "maxlat": b[2], "maxlon": b[3]}

    def union(boxes: list[Box | None]) -> Box | None:
        boxes = [b for b in boxes if b is not None]
        if not boxes:
            return None
        return min(x[0] for x in boxes), min(x[1] for x in boxes), max(x[2] for x in boxes), max(x[3] for x in boxes)

    facilities = FacilityIndex()
    for kinds, refs in fac_ways.values():
        if kinds and (b := box(refs)) is not None:
            facilities.add(kinds, b)
    for kinds, member_ids in fac_rels:
        if (b := union([box(fac_ways[w][1]) if w in fac_ways else box(ways[w][1]) if w in ways else None
                        for w in member_ids])) is not None:
            facilities.add(kinds, b)
    for kinds, lat, lon in fac_points:
        facilities.add(kinds, (lat, lon, lat, lon))

    def places_near(name: str, b: Box) -> list[str]:
        words = untyped_water.name_words(name)
        dlat = untyped_water.PLACE_NEAR_M / 111_320.0
        dlng = untyped_water.PLACE_NEAR_M / (111_320.0 * max(math.cos(math.radians((b[0] + b[2]) / 2)), 0.01))
        return sorted({
            place for place, lat, lon in places
            if b[0] - dlat <= lat <= b[2] + dlat and b[1] - dlng <= lon <= b[3] + dlng
            and untyped_water.contains_words(words, untyped_water.name_words(place))
        })

    def water(el: dict[str, Any], tags: dict[str, str], b: Box) -> dict[str, Any]:
        named = untyped_water.named_facilities(tags["name"]) if _is_untyped(tags) else set()
        if named:
            el["facilities_near"] = sorted(facilities.near(b, named, untyped_water.FACILITY_NEAR_M))
            el["places_near"] = places_near(tags["name"], b)
        return el

    for wid, (tags, nodes) in ways.items():
        if tags is None:
            continue
        b = box(nodes)
        if b is None:
            continue
        if _is_lake(tags):
            if in_state(outline, *b, code=code):
                elements.append(water({"type": "way", "id": wid, "tags": tags, "bounds": bounds(b)}, tags, b))
        else:
            elements.append({"type": "way", "id": wid, "tags": tags,
                             "center": {"lat": (b[0] + b[2]) / 2, "lon": (b[1] + b[3]) / 2}})
    for rid, (tags, member_ids) in relations.items():
        b = union([box(ways[w][1]) for w in member_ids if w in ways])
        if b is None:
            continue
        if in_state(outline, *b, code=code):
            elements.append(water({"type": "relation", "id": rid, "tags": tags, "bounds": bounds(b)}, tags, b))
    return {
        "generator": "FishEye geofabrik_lakes (pyosmium)",
        "extract_version": EXTRACT_VERSION,
        "source": f"{DOWNLOAD_BASE}/{BY_CODE[code].geofabrik}-latest.osm.pbf",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "elements": elements,
    }


# --------------------------------------------------------------------------
# Run, resumably
# --------------------------------------------------------------------------


@dataclass
class StateRun:
    code: str
    download_s: float = 0.0
    extract_s: float = 0.0
    import_s: float = 0.0
    lakes_created: int = 0
    lakes_updated: int = 0
    lakes_in_db: int = 0
    notes: list[str] = field(default_factory=list)


def _progress(out_dir: Path) -> dict[str, Any]:
    p = out_dir / "progress.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save_progress(out_dir: Path, progress: dict[str, Any]) -> None:
    p = out_dir / "progress.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(progress, indent=1), encoding="utf-8")
    os.replace(tmp, p)


def load_or_extract(code: str, pbf: Path, out_dir: Path) -> tuple[dict[str, Any], bool]:
    """The cached payload, or a fresh extract when there is none, the pbf is
    newer, or it came from another EXTRACT_VERSION. True when extracted."""
    out = out_dir / f"{code.lower()}_osm.json"
    if out.exists() and out.stat().st_mtime >= pbf.stat().st_mtime:
        payload = json.loads(out.read_text(encoding="utf-8"))
        if payload.get("extract_version", 1) == EXTRACT_VERSION:
            return payload, False
    payload = extract(pbf, code)
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(tmp, out)
    return payload, True


def count_untyped(code: str, pbf_dir: Path, out_dir: Path, samples: int = 15) -> dict[str, Any]:
    """What the untyped-water rules would add to one state, without opening
    the database: lakes kept by name alone (after merging with other pieces
    of the same lake), those left out by reason, and random names of each.
    Counts are before matching to lakes already stored (verified twins,
    CDFW-added lakes), so they can run a little high."""
    import random

    from app.data_import import osm_waterbody_import as osm
    from app.data_import import untyped_water

    pbf = pbf_dir / f"{BY_CODE[code].geofabrik}-latest.osm.pbf"
    if not pbf.exists():
        raise FileNotFoundError(f"{code}: {pbf} not downloaded; run the import once, or download it first")
    payload, _ = load_or_extract(code, pbf, out_dir)
    elements, _, skipped = osm.parse_elements(payload)
    lakes = osm.merge_pieces(elements)
    kept = [lake for lake in lakes if lake.untyped]
    left_out: dict[str, list[str]] = {}
    for el in payload["elements"]:
        tags = el.get("tags", {})
        name = tags.get("name", "").strip()
        if tags.get("natural") != "water" or tags.get("water", "").strip() or tags.get("landuse") == "reservoir":
            continue
        if osm._is_excluded_access(tags) or osm.private_by_name(name):
            continue
        reason = untyped_water.judge(name, tags, el.get("facilities_near"), el.get("places_near", ())).reason
        if reason != "ok":
            left_out.setdefault(reason, []).append(name)
    rnd = random.Random(code)
    by_type: dict[str, int] = {}
    for lake in kept:
        by_type[lake.water_type] = by_type.get(lake.water_type, 0) + 1
    # Facility words with no such facility mapped near: kept as place names.
    place_names = sorted(lake.name for lake in kept if untyped_water.named_facilities(lake.name))
    return {
        "facility_word_kept": len(place_names),
        "facility_word_kept_names": place_names,
        "typed_lakes": sum(1 for lake in lakes if not lake.untyped),
        "untyped_kept": len(kept),
        "untyped_kept_by_type": by_type,
        "untyped_likely_private": sum(1 for lake in kept if lake.likely_private),
        "left_out": {**{k: len(v) for k, v in sorted(left_out.items())},
                     "too_small": skipped.get("untyped_too_small", 0)},
        "kept_samples": sorted(rnd.sample([lake.name for lake in kept], min(samples, len(kept)))),
        "left_out_samples": {k: sorted(rnd.sample(v, min(8, len(v)))) for k, v in sorted(left_out.items())},
    }


def run_state(code: str, pbf_dir: Path, out_dir: Path, keep_pbf: bool = True) -> StateRun:
    from app.data_import import osm_waterbody_import as osm
    from app.db.session import SessionLocal
    from app.models.waterbody import State, Waterbody

    r = StateRun(code)
    t = time.monotonic()
    pbf = download(code, pbf_dir)
    r.download_s = time.monotonic() - t

    t = time.monotonic()
    payload, extracted = load_or_extract(code, pbf, out_dir)
    if extracted:
        r.extract_s = time.monotonic() - t

    t = time.monotonic()
    with SessionLocal() as db:
        summary = osm.run(code, payload, db)
        db.commit()
        state_id = db.scalar(select(State.id).where(State.code == code))
        r.lakes_in_db = db.scalar(select(func.count()).select_from(Waterbody).where(Waterbody.state_id == state_id)) or 0
    r.import_s = time.monotonic() - t
    r.lakes_created, r.lakes_updated = summary.lakes_created, summary.lakes_updated
    if not keep_pbf:
        pbf.unlink(missing_ok=True)
    return r


def report(out_dir: Path) -> None:
    from app.core.config import get_settings
    from app.db.session import SessionLocal
    from app.models.waterbody import State, Waterbody

    progress = _progress(out_dir)
    with SessionLocal() as db:
        rows = db.execute(
            select(State.code, State.name, func.count(Waterbody.id))
            .join(Waterbody, Waterbody.state_id == State.id, isouter=True)
            .group_by(State.code, State.name).order_by(State.code)
        ).all()
    total = 0
    print(f"{'state':5} {'lakes':>8}  {'extract s':>9} {'import s':>8}")
    for code, _name, n in rows:
        p = progress.get(code, {})
        total += n
        print(f"{code:5} {n:8d}  {p.get('extract_s', 0):9.0f} {p.get('import_s', 0):8.0f}")
    print(f"total lakes: {total}")
    url = get_settings().database_url
    if url.startswith("sqlite:///"):
        size = Path(url.removeprefix("sqlite:///")).stat().st_size
        print(f"SQLite file: {size / 1e6:.0f} MB")


def main(argv: list[str] | None = None) -> int:
    from app.db.session import SessionLocal, engine
    from app.db.upgrades import prepare_database

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--states", default="", help="comma-separated codes, or 'all'")
    ap.add_argument("--pbf-dir", type=Path, default=PBF_DIR)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--force", action="store_true", help="re-import states already marked done")
    ap.add_argument("--report", action="store_true", help="print lakes per state, timings and database size")
    ap.add_argument("--stop-above-mb", type=float, default=0,
                    help="stop (after the current state) once the SQLite file passes this size")
    ap.add_argument("--count-untyped", action="store_true",
                    help="only count what the untyped-water rules would add (payloads go to --out-dir; "
                         "untyped_count.json there); the database is not opened")
    args = ap.parse_args(argv)

    codes = [s.code for s in STATES] if args.states.lower() == "all" else [c.strip().upper() for c in args.states.split(",") if c.strip()]
    unknown = [c for c in codes if c not in BY_CODE]
    if unknown:
        print(f"unknown state codes: {', '.join(unknown)}", file=sys.stderr)
        return 2

    if args.count_untyped:
        if args.out_dir.resolve() == OUT_DIR.resolve():
            print("--count-untyped writes payloads; give it its own --out-dir, not the import's osm_cache",
                  file=sys.stderr)
            return 2
        args.out_dir.mkdir(parents=True, exist_ok=True)
        result_path = args.out_dir / "untyped_count.json"
        counts = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
        for code in codes:
            counts[code] = count_untyped(code, args.pbf_dir, args.out_dir)
            result_path.write_text(json.dumps(counts, indent=1), encoding="utf-8")
            c = counts[code]
            print(f"{code}: {c['typed_lakes']} tagged lakes, +{c['untyped_kept']} kept by name; "
                  f"left out {c['left_out']}", flush=True)
        return 0

    prepare_database(engine)
    with SessionLocal() as db:
        added = ensure_states(db)
        db.commit()
    if added:
        print(f"{added} state rows added")
    if args.report:
        report(args.out_dir)
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    progress = _progress(args.out_dir)
    for code in codes:
        if code in progress and not args.force:
            print(f"{code}: done earlier ({progress[code]['lakes_in_db']} lakes), skipped")
            continue
        r = run_state(code, args.pbf_dir, args.out_dir)
        progress[code] = {
            "finished_at": datetime.now(timezone.utc).isoformat(), "lakes_in_db": r.lakes_in_db,
            "created": r.lakes_created, "updated": r.lakes_updated,
            "download_s": round(r.download_s), "extract_s": round(r.extract_s), "import_s": round(r.import_s),
        }
        _save_progress(args.out_dir, progress)
        print(f"{code}: {r.lakes_in_db} lakes ({r.lakes_created} new, {r.lakes_updated} updated); "
              f"extract {r.extract_s:.0f}s, import {r.import_s:.0f}s", flush=True)
        if args.stop_above_mb:
            from app.core.config import get_settings

            url = get_settings().database_url
            if url.startswith("sqlite:///"):
                mb = Path(url.removeprefix("sqlite:///")).stat().st_size / 1e6
                if mb > args.stop_above_mb:
                    print(f"database is {mb:.0f} MB, over --stop-above-mb {args.stop_above_mb:.0f}: stopping")
                    return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
