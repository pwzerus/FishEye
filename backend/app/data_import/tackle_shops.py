"""Bait and tackle shops for the map, from the cached Geofabrik extracts.

OpenStreetMap (ODbL) is the only source, and only shops it maps:
- tagged as fishing or bait shops (`shop=fishing`, `shop=bait`);
- outdoor, sports and hunting shops tagged as selling fishing gear or bait
  (`fishing=yes|bait`, `sport=fishing`), or named for it ("… Fishing …");
- any shop whose name says bait or tackle: in Georgia's extract a third of
  them are mapped as convenience stores ("Lake Sinclair Bait And Tackle");
- the fishing retailers' stores (Bass Pro Shops, Cabela's, Academy Sports
  + Outdoors), by their `brand` tag.
"Outfitters" alone is not enough: in the same extract most are clothing.
Named shops only: an unnamed point is too often a stale or half-mapped one,
and a popup with no name says nothing.

Two steps, like geofabrik_lakes.py, reading the same extracts it already
downloaded (geofabrik_cache/, never fetched again here):

1. extract  osm_cache/tackle_shops.json: every state's shops, read with
            pyosmium in two filtered passes; a shop in an extract's border
            buffer counts for the state it is in (the Census outlines the
            map draws), and once;
2. import   the JSON into tackle_shops, keyed on the OpenStreetMap element,
            so a re-run updates rows and drops shops no longer mapped.

A server needs only the JSON: copy it up and run the import with
`--from-file`, with no extracts or pyosmium.

    python -m app.data_import.tackle_shops --states all
    python -m app.data_import.tackle_shops --from-file osm_cache/tackle_shops.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.data_import.geofabrik_lakes import OUT_DIR, PBF_DIR, Outline, _inside, load_outline
from app.data_import.provenance import source_record
from app.data_import.us_states import BY_CODE, STATES
from app.models.shop import KIND_BAIT, KIND_STORE, KIND_TACKLE, TackleShop

OUT_FILE = OUT_DIR / "tackle_shops.json"
SHOP_TYPES = {"fishing", "bait"}
# General shops that count only when tagged or named as selling fishing gear.
GEAR_SHOP_TYPES = {"outdoor", "sports", "hunting"}
FISHING_RETAILERS = {"bass pro shops", "cabela's", "academy sports + outdoors"}
BAIT_OR_TACKLE = re.compile(r"\b(bait|tackle)\b", re.IGNORECASE)
FISHING_WORD = re.compile(r"\bfishing\b", re.IGNORECASE)


def _clip(value: str | None, n: int) -> str | None:
    value = " ".join((value or "").split())
    return value[:n] or None


def shop_fields(tags: dict[str, str]) -> dict[str, Any] | None:
    """What FishEye keeps of an OpenStreetMap element, or None when it isn't
    a named fishing or bait shop."""
    name = _clip(tags.get("name"), 128)
    shop = tags.get("shop", "")
    if not name or not shop:
        return None
    sells_bait = (
        shop == "bait" or tags.get("fishing") == "bait" or tags.get("bait") == "yes" or bool(re.search(r"\bbait\b", name, re.I))
    )
    retailer = (tags.get("brand") or "").strip().lower() in FISHING_RETAILERS
    if shop in SHOP_TYPES or BAIT_OR_TACKLE.search(name):
        kind = KIND_BAIT if sells_bait else KIND_TACKLE
    elif shop in GEAR_SHOP_TYPES:
        sports = {s.strip() for s in tags.get("sport", "").split(";")}
        if retailer:
            kind = KIND_STORE
        elif tags.get("fishing") in ("yes", "bait") or "fishing" in sports or FISHING_WORD.search(name):
            kind = KIND_BAIT if sells_bait else KIND_TACKLE
        else:
            return None
    else:
        return None
    street = " ".join(p for p in (tags.get("addr:housenumber", ""), tags.get("addr:street", "")) if p)
    town = ", ".join(p for p in (tags.get("addr:city", ""), tags.get("addr:state", "")) if p)
    return {
        "name": name,
        "kind": kind,
        "address": _clip(", ".join(p for p in (street, town) if p), 200),
        "phone": _clip(tags.get("phone") or tags.get("contact:phone"), 40),
        "website": _website(tags.get("website") or tags.get("contact:website")),
        "opening_hours": _clip(tags.get("opening_hours"), 200),
    }


def _website(url: str | None) -> str | None:
    url = (url or "").strip().split(";")[0].strip()
    if not url:
        return None
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    return url[:300] if " " not in url else None


# --------------------------------------------------------------------------
# Extract
# --------------------------------------------------------------------------


def extract(pbf: Path, code: str, outline: Outline | None = None) -> list[dict[str, Any]]:
    """The named fishing and bait shops inside one state, from its extract."""
    import osmium
    from osmium.filter import IdFilter, KeyFilter

    outline = outline or load_outline(code)
    shops: list[dict[str, Any]] = []
    ways: dict[int, tuple[dict[str, Any], list[int]]] = {}
    for obj in osmium.FileProcessor(str(pbf), osmium.osm.NODE | osmium.osm.WAY).with_filter(KeyFilter("shop")):
        fields = shop_fields(dict(obj.tags))
        if fields is None:
            continue
        if isinstance(obj, osmium.osm.Node):
            shops.append({**fields, "osm_ref": f"n{obj.id}", "lat": obj.location.lat, "lng": obj.location.lon})
        else:
            # A building outline: its centre, from a few of its corners.
            refs = [n.ref for n in obj.nodes]
            ways[obj.id] = (fields, refs[:: max(1, len(refs) // 8)])
    if ways:
        needed = {r for _, refs in ways.values() for r in refs}
        where = {n.id: (n.location.lat, n.location.lon) for n in osmium.FileProcessor(str(pbf), osmium.osm.NODE).with_filter(IdFilter(needed))}
        for way_id, (fields, refs) in ways.items():
            pts = [where[r] for r in refs if r in where]
            if pts:
                lat = sum(p[0] for p in pts) / len(pts)
                lng = sum(p[1] for p in pts) / len(pts)
                shops.append({**fields, "osm_ref": f"w{way_id}", "lat": lat, "lng": lng})
    lng_shift = -360 if code == "AK" else 0
    return [
        {**s, "state": code, "lat": round(s["lat"], 6), "lng": round(s["lng"], 6)}
        for s in shops
        if _inside(outline, s["lng"] + (lng_shift if s["lng"] > 0 else 0), s["lat"])
    ]


def extract_all(codes: list[str], pbf_dir: Path = PBF_DIR) -> dict[str, Any]:
    seen: set[str] = set()
    shops: list[dict[str, Any]] = []
    for code in codes:
        pbf = pbf_dir / f"{BY_CODE[code].geofabrik}-latest.osm.pbf"
        if not pbf.with_name(pbf.name + ".done").exists():
            print(f"  {code}: no extract in {pbf_dir} (run geofabrik_lakes first); skipped", file=sys.stderr)
            continue
        found = [s for s in extract(pbf, code) if s["osm_ref"] not in seen]
        seen.update(s["osm_ref"] for s in found)
        shops.extend(found)
        print(f"  {code}: {len(found)} shops")
    return {
        "generator": "FishEye tackle_shops (pyosmium)",
        "extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "states": codes,
        "shops": shops,
    }


# --------------------------------------------------------------------------
# Import
# --------------------------------------------------------------------------


def run(db: Session, payload: dict[str, Any]) -> dict[str, int]:
    """Upserts the payload's shops; drops shops of its states no longer in it."""
    retrieved = datetime.fromisoformat(payload["extracted_at"]).replace(tzinfo=None)
    record = source_record(db, "osm_shops", retrieved)
    existing = {s.osm_ref: s for s in db.scalars(select(TackleShop).where(TackleShop.state_code.in_(payload["states"])))}
    added = updated = 0
    keep: set[str] = set()
    for s in payload["shops"]:
        keep.add(s["osm_ref"])
        row = existing.get(s["osm_ref"]) or db.scalar(select(TackleShop).where(TackleShop.osm_ref == s["osm_ref"]))
        if row is None:
            row = TackleShop(osm_ref=s["osm_ref"])
            db.add(row)
            added += 1
        else:
            updated += 1
        row.name, row.kind = s["name"], s["kind"]
        row.latitude, row.longitude, row.state_code = s["lat"], s["lng"], s["state"]
        row.address, row.phone, row.website = s.get("address"), s.get("phone"), s.get("website")
        row.opening_hours = s.get("opening_hours")
        row.source_record_id = record.id
    gone = [ref for ref in existing if ref not in keep]
    if gone:
        db.execute(delete(TackleShop).where(TackleShop.osm_ref.in_(gone)))
    db.commit()
    return {"added": added, "updated": updated, "removed": len(gone)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--states", default="all", help="all, or codes like TX,GA")
    parser.add_argument("--from-file", type=Path, help="import this payload; no extracts needed")
    parser.add_argument("--extract-only", action="store_true")
    args = parser.parse_args(argv)

    if args.from_file:
        payload = json.loads(args.from_file.read_text(encoding="utf-8"))
    else:
        codes = [s.code for s in STATES] if args.states == "all" else [c.strip().upper() for c in args.states.split(",")]
        unknown = [c for c in codes if c not in BY_CODE]
        if unknown:
            parser.error(f"unknown state codes: {unknown}")
        payload = extract_all(codes)
        OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        print(f"{len(payload['shops'])} shops in {len(codes)} states -> {OUT_FILE}")
        if args.extract_only:
            return 0

    from app.db.session import SessionLocal, engine
    from app.db.upgrades import prepare_database

    prepare_database(engine)
    with SessionLocal() as db:
        counts = run(db, payload)
    print(f"tackle_shops: {counts['added']} added, {counts['updated']} updated, {counts['removed']} removed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
