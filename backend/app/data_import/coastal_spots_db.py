"""Import osm_cache/coastal_spots.json (data_import/coastal_spots.py) and, in
California, CDFW's public piers (data_import/cdfw_piers.py) into
coastal_spots. A pier both list becomes one spot: CDFW's name, kind and
license facts, OpenStreetMap's position, hours, fee and lights. Spots are
upserted by their source's id and a state's spots no longer listed are
removed. No pyosmium or extracts needed, so a server runs only this:

    python -m app.data_import.coastal_spots --from-file osm_cache/coastal_spots.json
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.data_import.provenance import source_record
from app.models.coastal_spot import COASTS, KINDS, LICENSE_NOTES, CoastalSpot

# An agency's pier and an OpenStreetMap spot are the same place when they
# are this close, or a little further when their names share a word.
MATCH_M = 200.0
MATCH_NAMED_M = 600.0  # a long pier: CDFW marks its foot, OSM its middle (Dumbarton Pier)
# Other OSM spots of the same pier (its way and a fishing node on it, say)
# within this of a matched one, sharing a word of the name, fold into it.
ABSORB_M = 250.0
# Two OSM spots this close are one place when their names allow it; the
# same kind with a shared name word, a little further (Caldwell Pier and
# Horace Caldwell Pier, Port Aransas: one pier mapped twice).
DUPLICATE_M = 80.0
SAME_NAME_M = 300.0
GENERIC = {"pier", "piers", "fishing", "wharf", "jetty", "jetties", "the", "public", "park", "of", "and", "at",
           "street", "st", "beach", "harbor", "harbour", "bay", "point", "pt", "north", "south", "east", "west",
           "municipal", "city", "county", "state", "pleasure", "access", "area", "mole", "breakwater"}
OSM_ONLY_KINDS = ("boat_ramp",)


def _metres(a: dict[str, Any], b: dict[str, Any]) -> float:
    cos = math.cos(math.radians((a["lat"] + b["lat"]) / 2))
    return math.hypot((a["lat"] - b["lat"]) * 111_320, (a["lng"] - b["lng"]) * 111_320 * cos)


def _tokens(name: str | None) -> list[str]:
    # "Stearn's Wharf" and "Stearns Wharf" are one name.
    return re.findall(r"[a-z0-9]+", (name or "").lower().replace("'", "").replace("’", ""))


def _words(name: str | None) -> set[str]:
    return {w for w in _tokens(name) if w not in GENERIC and len(w) > 1}


def _shares_name(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """A word in common and the same numbers; or two jetties on the same side
    ("Bodega Bay South Jetty" and OSM's "South Jetty")."""
    if not a.get("name") or not b.get("name"):
        return False
    digits = re.compile(r"\d+")
    if _words(a["name"]) & _words(b["name"]) and digits.findall(a["name"]) == digits.findall(b["name"]):
        return True
    sides = {"north", "south", "east", "west"}
    da, db = sides & set(_tokens(a["name"])), sides & set(_tokens(b["name"]))
    return bool(da) and da == db and a["kind"] == b["kind"] == "jetty"


def _same_place_names(a: str | None, b: str | None) -> bool:
    """Could these name one place? One unnamed, or a shared word and the same
    numbers ("Pier 1" and "Pier 2" are two piers)."""
    if not a or not b or a.strip().lower() == b.strip().lower():
        return True
    digits = re.compile(r"\d+")
    return bool(_words(a) & _words(b)) and digits.findall(a) == digits.findall(b)


def dedupe(osm: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """OpenStreetMap often maps one pier twice (two ways, or a way and a
    fishing node on it). Spots this close that could be one place are one:
    the named, fishing-tagged way is kept."""
    def rank(s: dict[str, Any]) -> tuple[bool, bool, bool]:
        return (bool(s.get("name")), bool(s.get("fishing_tagged")), not s["osm_ref"].startswith("n"))

    cell = 0.003  # degrees, about 300 m: neighbours are within the 3x3 cells around
    grid: dict[tuple[int, int], list[dict[str, Any]]] = {}
    kept: list[dict[str, Any]] = []
    for s in sorted(osm, key=rank, reverse=True):
        ci, cj = int(s["lat"] // cell), int(s["lng"] // cell)
        dup = False
        for k in (k for di in (-1, 0, 1) for dj in (-1, 0, 1) for k in grid.get((ci + di, cj + dj), [])):
            ramps = (s["kind"] == "boat_ramp") + (k["kind"] == "boat_ramp")
            if ramps == 1 or k["state"] != s["state"]:
                continue
            d = _metres(s, k)
            if ramps == 2:
                dup = d <= 40
            elif d <= DUPLICATE_M:
                dup = _same_place_names(s.get("name"), k.get("name"))
            elif d <= SAME_NAME_M and s["kind"] == k["kind"] and s.get("name") and k.get("name"):
                dup = _same_place_names(s["name"], k["name"])
            if dup:
                break
        if not dup:
            kept.append(s)
            grid.setdefault((ci, cj), []).append(s)
    return kept


def merge(osm: list[dict[str, Any]], agency: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One list of spots, each with "ref", "source" and "osm_ref": OSM's
    duplicates folded (dedupe), then agency piers matched one to one with the
    nearest OSM pier, jetty or fishing spot (closest pairs first), the rest
    of both kept as they are."""
    osm = dedupe(osm)
    for s in osm:
        s.setdefault("ref", s["osm_ref"])
        s.setdefault("source", "osm")
    pairs = []
    for ai, a in enumerate(agency):
        for oi, o in enumerate(osm):
            if o["kind"] in OSM_ONLY_KINDS or o["state"] != a["state"]:
                continue
            d = _metres(a, o)
            shared = _shares_name(a, o)
            if d <= MATCH_M or (shared and d <= MATCH_NAMED_M):
                pairs.append((d - (150 if shared else 0), ai, oi))
    matched: dict[int, int] = {}
    used: set[int] = set()
    for _, ai, oi in sorted(pairs):
        if ai not in matched and oi not in used:
            matched[ai] = oi
            used.add(oi)
    # A second OSM element of a pier already matched (Shelter Island Pier is
    # mapped as two ways) would show as a second marker on top of it.
    for ai, oi in matched.items():
        words = _words(agency[ai]["name"]) | _words(osm[oi].get("name"))
        for oj, o in enumerate(osm):
            if oj in used or o["kind"] in OSM_ONLY_KINDS or o["state"] != osm[oi]["state"]:
                continue
            if _metres(osm[oi], o) <= ABSORB_M and (words & _words(o.get("name")) or not o.get("name")):
                used.add(oj)
    out = [o for oi, o in enumerate(osm) if oi not in used]
    for ai, a in enumerate(agency):
        spot = {**a, "source": a["ref"].split(":", 1)[0], "osm_ref": None}
        oi = matched.get(ai)
        if oi is not None:
            o = osm[oi]
            spot.update(
                osm_ref=o["osm_ref"], lat=o["lat"], lng=o["lng"], fee=o.get("fee"), opening_hours=o.get("opening_hours"),
                lit=bool(o.get("lit")), operator=o.get("operator"), website=o.get("website"),
            )
        out.append(spot)
    return out


def run(db: Session, payload: dict[str, Any], agency: list[dict[str, Any]] | None = None,
        agency_retrieved: datetime | None = None) -> dict[str, int]:
    retrieved = datetime.fromisoformat(payload["extracted_at"]).replace(tzinfo=None)
    records = {"osm": source_record(db, "osm_coastal_spots", retrieved)}
    if agency:
        records["cdfw"] = source_record(db, "cdfw_ds3090", agency_retrieved or retrieved)
    states = set(payload["states"]) | {a["state"] for a in agency or []}
    spots = merge([dict(s) for s in payload["spots"]], [dict(a) for a in agency or []])
    existing = {s.ref: s for s in db.scalars(select(CoastalSpot).where(CoastalSpot.state_code.in_(states)))}
    added = updated = 0
    keep: set[str] = set()
    for s in spots:
        if s["kind"] not in KINDS or s["coast"] not in COASTS or s["ref"] in keep:
            continue
        keep.add(s["ref"])
        row = existing.get(s["ref"]) or db.scalar(select(CoastalSpot).where(CoastalSpot.ref == s["ref"]))
        if row is None:
            row = CoastalSpot(ref=s["ref"])
            db.add(row)
            added += 1
        else:
            updated += 1
        row.source, row.osm_ref = s["source"], s.get("osm_ref")
        row.name, row.kind, row.coast = s.get("name"), s["kind"], s["coast"]
        row.latitude, row.longitude, row.state_code = s["lat"], s["lng"], s["state"]
        row.fishing_tagged, row.lit = bool(s.get("fishing_tagged")), bool(s.get("lit"))
        row.fee, row.opening_hours = s.get("fee"), s.get("opening_hours")
        row.operator, row.website = s.get("operator"), s.get("website")
        row.no_license = bool(s.get("no_license"))
        row.license_note = s.get("license_note") if s.get("license_note") in LICENSE_NOTES else None
        row.source_record_id = records[s["source"]].id
    gone = [ref for ref in existing if ref not in keep]
    if gone:
        db.execute(delete(CoastalSpot).where(CoastalSpot.ref.in_(gone)))
    db.commit()
    return {"added": added, "updated": updated, "removed": len(gone)}


def import_file(path: Path) -> dict[str, int]:
    """The OSM spots in `path`, with CDFW's piers merged in (fetched once into
    cdfw_cache/ when missing)."""
    from app.data_import import cdfw_piers
    from app.db.session import SessionLocal

    payload = json.loads(Path(path).read_text("utf-8"))
    cache = cdfw_piers.fetch()
    agency = cdfw_piers.read(cache)
    fetched = datetime.fromtimestamp(cache.stat().st_mtime)
    with SessionLocal() as db:
        return run(db, payload, agency, fetched)
