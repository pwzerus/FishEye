"""Is the lake on land the public may enter? From PAD-US (USGS, public domain).

See docs/adr/0034-california-official-data.md and docs/data-sources.md.
PAD-US is the national inventory of parks, forests, refuges and other
protected land; its Public Access attribute says whether the public may
enter: OA open, RA restricted (permit, season, hours), XA closed, UK
unknown. This importer marks each lake whose centre lies in an OA or RA
area (Waterbody.public_land, public_land_name, public_land_manager).

What it says, and what it doesn't: a lake inside a national forest or a
county park is very likely reachable by the public; that is useful above
all for the OpenStreetMap lakes FishEye otherwise knows nothing about. It
is not a confirmed entrance, and it does not change public_access_status
or any access point. A lake outside PAD-US is not therefore private.

Fetch (network), per state: the state's lake centres go to USGS's PAD-US
Public Access feature service as multipoint queries, 400 at a time; only
OA/RA areas that contain a lake come back, simplified to ~20 m, and are
saved to padus_cache/<state>_public_access.json. The import is offline:
a point-in-polygon test in plain Python, so the server needs no GIS library.

    python -m app.data_import.padus_import --state CA --fetch
    python -m app.data_import.padus_import --state CA
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data_import.provenance import USER_AGENT, link_dataset, source_record, unlink_dataset
from app.models.waterbody import State, Waterbody

LAYER = "https://services.arcgis.com/v01gqwM5QqNysAAi/ArcGIS/rest/services/PADUS_Public_Access/FeatureServer/0"
DEFAULT_CACHE = Path("padus_cache")
BATCH = 400
REQUEST_DELAY_S = 1.0
OUT_FIELDS = "OBJECTID,Unit_Nm,Pub_Access,MngNm_Desc,MngTp_Desc,DesTp_Desc"
ACCESS = {"OA": "open", "RA": "restricted"}


@dataclass(frozen=True)
class Area:
    object_id: int
    name: str
    access: str  # open | restricted
    manager: str
    designation: str
    rings: tuple[tuple[tuple[float, float], ...], ...]  # (lng, lat) rings
    bbox: tuple[float, float, float, float]  # west, south, east, north


def parse_areas(features: list[dict[str, Any]]) -> list[Area]:
    out = []
    for f in features:
        a = f.get("attributes") or {}
        access = ACCESS.get((a.get("Pub_Access") or "").strip())
        rings = tuple(tuple((float(x), float(y)) for x, y, *_ in ring) for ring in (f.get("geometry") or {}).get("rings") or [])
        if access is None or not rings:
            continue
        xs = [p[0] for r in rings for p in r]
        ys = [p[1] for r in rings for p in r]
        out.append(Area(
            int(a["OBJECTID"]), (a.get("Unit_Nm") or "").strip(), access,
            (a.get("MngNm_Desc") or "").strip(), (a.get("DesTp_Desc") or "").strip(),
            rings, (min(xs), min(ys), max(xs), max(ys)),
        ))
    return out


def contains(area: Area, lat: float, lng: float) -> bool:
    """Even-odd ray casting over every ring, so holes (islands of private
    land inside a forest) count as outside."""
    w, s, e, n = area.bbox
    if not (w <= lng <= e and s <= lat <= n):
        return False
    inside = False
    for ring in area.rings:
        j = len(ring) - 1
        for i in range(len(ring)):
            xi, yi = ring[i]
            xj, yj = ring[j]
            if (yi > lat) != (yj > lat) and lng < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
    return inside


def best_area(areas: list[Area], lat: float, lng: float) -> Area | None:
    """The area a lake lies in: open beats restricted; then the smallest
    (a county park inside a national forest says more)."""
    hits = [a for a in areas if contains(a, lat, lng)]
    if not hits:
        return None
    return min(hits, key=lambda a: (a.access != "open", (a.bbox[2] - a.bbox[0]) * (a.bbox[3] - a.bbox[1])))


def fetch(db: Session, state_code: str, cache: Path) -> Path:
    import httpx

    state = db.scalar(select(State).where(State.code == state_code))
    if state is None:
        raise SystemExit(f"No {state_code} lakes in the database.")
    points = [(wb.longitude, wb.latitude) for wb in db.scalars(select(Waterbody).where(Waterbody.state_id == state.id))]
    seen: dict[int, dict[str, Any]] = {}
    with httpx.Client(timeout=180, headers={"User-Agent": USER_AGENT}) as client:
        for start in range(0, len(points), BATCH):
            batch = points[start : start + BATCH]
            data = {
                "where": "Pub_Access IN ('OA','RA')",
                "geometry": json.dumps({"points": [[round(x, 6), round(y, 6)] for x, y in batch], "spatialReference": {"wkid": 4326}}),
                "geometryType": "esriGeometryMultipoint", "inSR": "4326", "spatialRel": "esriSpatialRelIntersects",
                "outFields": OUT_FIELDS, "returnGeometry": "true", "outSR": "4326",
                "maxAllowableOffset": "0.0002", "geometryPrecision": "5", "f": "json",
            }
            for attempt in range(4):
                resp = client.post(f"{LAYER}/query", data=data)
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                    time.sleep(5 * 2**attempt)
                    continue
                resp.raise_for_status()
                break
            body = resp.json()
            if "error" in body:
                raise RuntimeError(body["error"])
            for f in body.get("features") or []:
                seen[f["attributes"]["OBJECTID"]] = f
            print(f"  {min(start + BATCH, len(points))}/{len(points)} lakes queried, {len(seen)} areas so far")
            time.sleep(REQUEST_DELAY_S)
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{state_code.lower()}_public_access.json"
    path.write_text(json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(), "source": LAYER, "features": list(seen.values()),
    }), encoding="utf-8")
    return path


@dataclass
class ImportSummary:
    lakes: int = 0
    by_access: Counter[str] = field(default_factory=Counter)
    by_tier: Counter[str] = field(default_factory=Counter)
    cleared: int = 0


def run(db: Session, state_code: str, payload: dict[str, Any]) -> ImportSummary:
    state = db.scalar(select(State).where(State.code == state_code))
    if state is None:
        raise ValueError(f"No {state_code} lakes in the database.")
    stamp = payload.get("fetched_at")
    fetched = datetime.fromisoformat(stamp).astimezone(timezone.utc).replace(tzinfo=None) if stamp else datetime.now(timezone.utc).replace(tzinfo=None)
    record = source_record(db, "padus_4_1", fetched)
    areas = parse_areas(payload.get("features") or [])
    summary = ImportSummary()
    credited: set[int] = set()
    for wb in db.scalars(select(Waterbody).where(Waterbody.state_id == state.id)):
        summary.lakes += 1
        area = best_area(areas, wb.latitude, wb.longitude)
        if area is None:
            if wb.public_land is not None:
                summary.cleared += 1
            wb.public_land = wb.public_land_name = wb.public_land_manager = None
            continue
        wb.public_land = area.access
        # PAD-US fills unknown fields with the word "Unknown".
        name = next((n for n in (area.name, area.designation) if n and n.lower() != "unknown"), None)
        wb.public_land_name = name[:160] if name else None
        wb.public_land_manager = area.manager[:64] if area.manager and area.manager.lower() != "unknown" else None
        link_dataset(db, wb, record, f"padus:{area.object_id}", f"{LAYER}/{area.object_id}")
        credited.add(wb.id)
        summary.by_access[area.access] += 1
        summary.by_tier[f"{wb.data_tier}/{area.access}"] += 1
    db.flush()
    # Lakes of other states keep their links; only this state's are re-decided.
    others = {
        wid for wid in db.scalars(select(Waterbody.id).where(Waterbody.state_id != state.id))
    }
    unlink_dataset(db, record, credited | others)
    return summary


def main(argv: list[str] | None = None) -> int:
    from app.db.session import SessionLocal, engine
    from app.db.upgrades import prepare_database

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", required=True)
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--fetch", action="store_true", help="query PAD-US for this state's lakes first (network)")
    args = ap.parse_args(argv)
    code = args.state.upper()
    prepare_database(engine)
    path = args.cache / f"{code.lower()}_public_access.json"
    with SessionLocal() as db:
        if args.fetch:
            fetch(db, code, args.cache)
        if not path.exists():
            print(f"No {path}: run with --fetch first.", file=sys.stderr)
            return 2
        summary = run(db, code, json.loads(path.read_text(encoding="utf-8")))
        db.commit()
    print(f"{code}: {summary.lakes} lakes; on publicly accessible land: {summary.by_access['open']} open, "
          f"{summary.by_access['restricted']} restricted; cleared since last run: {summary.cleared}")
    print("  by tier: " + ", ".join(f"{k}={v}" for k, v in sorted(summary.by_tier.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
