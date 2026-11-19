"""Public saltwater fishing spots for the map: piers, jetties, wharves and
mapped fishing spots on the coast of every coastal state, Alaska and Hawaii
included, from Geofabrik's OpenStreetMap extracts (ODbL), offline.

The owner asked for them on 2026-11-18: at the coast there are no lakes, but
there are fishing piers and jetties anglers can walk onto. "Coastal" means
within about a kilometre of OpenStreetMap's coastline (natural=coastline),
which OSM draws along the sea, bays and estuaries but not the Great Lakes.

What counts as a spot, by OSM tags:
- **pier**: man_made=pier marked for fishing (fishing=yes|designated, or
  leisure=fishing on it), or named as a fishing pier; or a named pier or
  wharf that isn't private and isn't a ferry, cruise, navy or marina dock;
- **jetty**: man_made=breakwater|groyne marked for fishing, or named a jetty;
- **fishing spot**: leisure=fishing that isn't private;
- **boat ramp**: leisure=slipway that isn't private (small-boat anglers).
Private (access=private|no) is always left out; fee, opening hours, lights
and the operator are kept when mapped.

Per state, the extract is downloaded (geofabrik_lakes.download), read in
three filtered pyosmium passes, and deleted again unless --keep: the owner
asked that the large files go once their spots are out. What stays is
osm_cache/coastal_spots.json, which is all a server needs:

    python -m app.data_import.coastal_spots --states coastal          # download, extract, delete
    python -m app.data_import.coastal_spots --from-file osm_cache/coastal_spots.json   # import
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.data_import.geofabrik_lakes import OUT_DIR, PBF_DIR, _inside, download, in_state, load_outline
from app.data_import.us_states import BY_CODE

COASTAL = ("AL", "AK", "CA", "CT", "DE", "FL", "GA", "HI", "LA", "ME", "MD", "MA", "MS", "NH", "NJ", "NY", "NC",
           "OR", "RI", "SC", "TX", "VA", "WA")
OUT = OUT_DIR / "coastal_spots.json"
# Bumped when extract() takes different elements; a payload from another
# version is extracted again. 2: relations, any part on the coast, named
# jetties drawn as piers, fishing-tagged bridges and walls. 3: the state is
# the one whose county (Census, ~100 m) holds a point of the spot.
VERSION = 3
CELL = 0.01  # degrees; a spot counts as coastal when its cell or a neighbour holds coastline
# A spot wholly at sea, in no county (a breakwater offshore, a fishing node
# at a pier's end), counts when it is this near the state's 1:10M outline...
STATE_MARGIN_M = 1500.0
# ...unless it is on a foreign shore that close to the border, which has no
# US county either: (south, west, north, east).
FOREIGN = (
    (32.30, -117.30, 32.534, -116.90),  # Tijuana, south of the California line
    (25.70, -97.40, 25.955, -97.10),  # Playa Bagdad, south of the Rio Grande's mouth
    (49.0, -123.40, 49.20, -122.60),  # White Rock and Boundary Bay, north of the 49th parallel
    (44.82, -66.975, 45.06, -66.85),  # Campobello Island, New Brunswick
    (55.90, -130.0, 56.00, -129.90),  # Stewart, across the Portland Canal from Hyder, Alaska
)
PRIVATE = {"private", "no", "customers", "permit"}
NOT_FISHING_PIER = re.compile(
    r"\b(ferry|cruise|terminal|navy|naval|army|military|uss|coast guard|patrol|base|marina|yacht|dock|docks|"
    r"private|club|condo|boat ?house|fuel|container|cargo|oil|lng|ship ?yard|shipyard|industrial|loading|"
    r"seaplane|restaurant|mooring|quay|berth|warehouse|grain|coal|research|noaa|nmfs|uscg|usace|refinery|lifeboat)\b",
    re.I,
)
# A pier named only by a number or a code ("38", "K10", "Pier 51A") is a
# harbour berth: a name has to have a word of its own besides pier or wharf.
OWN_WORD = re.compile(r"\b(?!pier\b|wharf\b)[a-z]{3,}\b", re.I)
JETTY = re.compile(r"\bjett(y|ies)\b", re.I)
# A business that takes people fishing, not a place they can walk to.
BUSINESS = re.compile(r"\b(charters?|guide service|guides|outfitters?|tackle|bait shop|lodge|resort|rentals?)\b", re.I)
# The tag keys a spot can come from (pyosmium's first, filtered pass).
SPOT_KEYS = ("man_made", "leisure", "fishing")
# Marked for fishing, but water or land rather than a spot on the shore (a
# beach marked for fishing is a spot: surf fishing).
NOT_A_SPOT = {"water", "waterway", "landuse", "building", "boundary", "place"}
WATER = {"water", "wetland", "bay", "strait", "spring"}


def _clip(value: str | None, n: int) -> str | None:
    value = (value or "").strip()
    return value[:n] if value else None


def spot_kind(tags: dict[str, str]) -> str | None:
    """What this OSM element is to an angler, or None to leave it out."""
    if tags.get("access") in PRIVATE:
        return None
    name = tags.get("name", "")
    fishing = tags.get("fishing") in ("yes", "designated") or tags.get("leisure") == "fishing"
    if tags.get("fishing") in ("no", "private"):
        return None
    if BUSINESS.search(name) and tags.get("leisure") != "slipway":
        return None
    man_made = tags.get("man_made")
    if man_made == "pier":
        if JETTY.search(name):
            return "jetty"  # a jetty mappers drew as a pier (Bodega Bay's)
        if fishing or re.search(r"fishing", name, re.I):
            return "pier"
        if (
            re.search(r"\b(pier|wharf)\b", name, re.I)
            and OWN_WORD.search(name)
            and not NOT_FISHING_PIER.search(name)
            and tags.get("mooring") not in ("yes", "private")
        ):
            return "pier"
        return None
    if man_made in ("breakwater", "groyne"):
        if fishing or JETTY.search(name):
            return "jetty"
        return None
    if tags.get("leisure") == "fishing":
        return "fishing_spot"
    if tags.get("leisure") == "slipway":
        return "boat_ramp"
    if tags.get("leisure") in ("park", "nature_reserve", "recreation_ground"):
        if re.search(r"\bfishing pier\b", name, re.I):
            return "pier"
        if re.search(r"\bjetty park\b", name, re.I):
            return "jetty"  # "Jetty Park": the park at a jetty's foot, not "Jetty View Park"
    if fishing and not NOT_A_SPOT.intersection(tags) and tags.get("natural") not in WATER:
        # A bridge, seawall, catwalk or park marked for fishing. Water marked
        # for fishing is a lake or a river, which the lakes cover.
        return "fishing_spot"
    return None


def spot_fields(tags: dict[str, str]) -> dict[str, Any] | None:
    kind = spot_kind(tags)
    if kind is None:
        return None
    return {
        "kind": kind,
        "name": _clip(tags.get("name"), 160),
        "fishing_tagged": tags.get("fishing") in ("yes", "designated") or tags.get("leisure") == "fishing",
        "fee": _clip(tags.get("fee"), 40),
        "opening_hours": _clip(tags.get("opening_hours"), 120),
        "lit": tags.get("lit") == "yes",
        "operator": _clip(tags.get("operator"), 120),
        "website": _clip(tags.get("website") or tags.get("contact:website"), 300),
    }


def coast_of(code: str, lat: float, lng: float) -> str:
    """Which coast: atlantic, gulf, pacific, alaska or hawaii."""
    if code == "AK":
        return "alaska"
    if code == "HI":
        return "hawaii"
    if code in ("CA", "OR", "WA"):
        return "pacific"
    if code in ("TX", "LA", "MS", "AL"):
        return "gulf"
    if code == "FL":
        # The peninsula's west side and the panhandle face the Gulf; the Keys
        # and the east side the Atlantic.
        return "gulf" if (lng < -81.6 and lat > 24.9) or lat > 29.5 and lng < -83.0 else "atlantic"
    return "atlantic"


def state_of(points: list[tuple[float, float]]) -> str | None:
    """The state whose county (Census 1:500k, ~100 m) holds a point of the
    spot; None when every point is at sea or outside the US (Canada, Mexico).
    A state's extract reaches a few kilometres past its border, and the
    1:10M outline is too coarse to say which side a pier is on."""
    from app.services.counties import county_at

    for lat, lng in points:
        county = county_at(lat, lng)
        if county is not None:
            return county.state
    return None


def _sample(refs: list[int], n: int = 8) -> list[int]:
    """A few of a way's nodes, both ends included."""
    return refs[:: max(1, len(refs) // n)] + refs[-1:]


def extract(pbf: Path, code: str) -> list[dict[str, Any]]:
    import osmium
    from osmium.filter import IdFilter, KeyFilter, TagFilter

    outline = load_outline(code)
    nodes: list[tuple[dict[str, Any], str, tuple[float, float]]] = []
    ways: dict[int, tuple[dict[str, Any], list[int]]] = {}
    rels: dict[int, tuple[dict[str, Any], list[int]]] = {}
    kinds = osmium.osm.NODE | osmium.osm.WAY | osmium.osm.RELATION
    for obj in osmium.FileProcessor(str(pbf), kinds).with_filter(KeyFilter(*SPOT_KEYS)):
        tags = dict(obj.tags)
        fields = spot_fields(tags)
        if fields is None:
            continue
        if isinstance(obj, osmium.osm.Node):
            nodes.append((fields, f"n{obj.id}", (obj.location.lat, obj.location.lon)))
        elif isinstance(obj, osmium.osm.Way):
            ways[obj.id] = (fields, _sample([n.ref for n in obj.nodes]))
        elif tags.get("type") == "multipolygon":
            # A big pier drawn as an area with holes (Santa Monica's, say).
            rels[obj.id] = (fields, [m.ref for m in obj.members if m.type == "w" and m.role in ("outer", "")])
    # Coastline: every fifth node is plenty for 1 km cells. And the outer
    # ways of the multipolygon spots, for their nodes.
    coast_refs: set[int] = set()
    for w in osmium.FileProcessor(str(pbf), osmium.osm.WAY).with_filter(TagFilter(("natural", "coastline"))):
        coast_refs.update(n.ref for n in list(w.nodes)[::5])
    member_refs: dict[int, list[int]] = {}
    member_ids = {w for _, ids in rels.values() for w in ids}
    if member_ids:
        for w in osmium.FileProcessor(str(pbf), osmium.osm.WAY).with_filter(IdFilter(member_ids)):
            member_refs[w.id] = _sample([n.ref for n in w.nodes], 4)
    rel_refs = {rid: [r for w in ids for r in member_refs.get(w, [])] for rid, (_, ids) in rels.items()}
    needed = coast_refs | {r for _, refs in ways.values() for r in refs} | {r for refs in rel_refs.values() for r in refs}
    where: dict[int, tuple[float, float]] = {}
    if needed:
        for n in osmium.FileProcessor(str(pbf), osmium.osm.NODE).with_filter(IdFilter(needed)):
            where[n.id] = (n.location.lat, n.location.lon)
    cells = {(int(where[r][0] // CELL), int(where[r][1] // CELL)) for r in coast_refs if r in where}

    found = [(fields, ref, [pt]) for fields, ref, pt in nodes]
    found += [(fields, f"w{wid}", [where[r] for r in refs if r in where]) for wid, (fields, refs) in ways.items()]
    found += [(fields, f"r{rid}", [where[r] for r in rel_refs[rid] if r in where]) for rid, (fields, _) in rels.items()]

    def coastal(lat: float, lng: float) -> bool:
        ci, cj = int(lat // CELL), int(lng // CELL)
        return any((ci + di, cj + dj) in cells for di in (-1, 0, 1) for dj in (-1, 0, 1))

    def near_outline(lat: float, lng: float) -> bool:
        if any(s <= lat <= n and w <= lng <= e for s, w, n, e in FOREIGN):
            return False
        if _inside(outline, lng - 360 if code == "AK" and lng > 0 else lng, lat):
            return True
        return in_state(outline, lat, lng, lat, lng, code, STATE_MARGIN_M)

    out = []
    for fields, ref, pts in found:
        # Coastal when any part of it is: a long jetty's middle is far out at sea.
        if not pts or not any(coastal(*p) for p in pts):
            continue
        lat, lng = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        # The extract reaches past the border: the state is where its foot is.
        state = state_of(pts)
        if state is not None and state != code:
            continue
        if state is None and not (near_outline(lat, lng) or any(near_outline(*p) for p in pts)):
            continue
        out.append({**fields, "osm_ref": ref, "state": code, "coast": coast_of(code, lat, lng),
                    "lat": round(lat, 6), "lng": round(lng, 6)})
    return out


def extract_all(codes: list[str], keep: bool = False, pbf_dir: Path = PBF_DIR) -> dict[str, Any]:
    payload = json.loads(OUT.read_text("utf-8")) if OUT.exists() else {"spots": [], "states": []}
    if payload.get("version") != VERSION:
        payload = {"spots": [], "states": []}
    done = set(payload.get("states", []))
    spots = [s for s in payload["spots"] if s["state"] not in codes or s["state"] in done]
    seen = {s["osm_ref"] for s in spots}
    for code in codes:
        if code in done:
            print(f"  {code}: already extracted")
            continue
        pbf = download(code, pbf_dir)
        found = [s for s in extract(pbf, code) if s["osm_ref"] not in seen]
        seen.update(s["osm_ref"] for s in found)
        spots.extend(found)
        done.add(code)
        counts = {k: sum(s["kind"] == k for s in found) for k in ("pier", "jetty", "fishing_spot", "boat_ramp")}
        print(f"  {code}: {len(found)} spots {counts}", flush=True)
        payload = {
            "version": VERSION,
            "generator": "FishEye coastal_spots (pyosmium)",
            "source": "OpenStreetMap contributors, ODbL 1.0, via Geofabrik",
            "extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "states": sorted(done),
            "spots": spots,
        }
        OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8", newline="\n")
        if not keep:
            # The owner, 2026-11-18: delete the extracts once their spots are out.
            pbf.unlink(missing_ok=True)
            pbf.with_name(pbf.name + ".done").unlink(missing_ok=True)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--states", default="coastal", help='"coastal" or a comma list (CA,TX)')
    parser.add_argument("--keep", action="store_true", help="keep the downloaded extracts")
    parser.add_argument("--from-file", type=Path, help="import this JSON into the database instead")
    args = parser.parse_args(argv)
    if args.from_file:
        from app.data_import.coastal_spots_db import import_file

        print(import_file(args.from_file))
        return 0
    codes = list(COASTAL) if args.states == "coastal" else [c.strip().upper() for c in args.states.split(",")]
    bad = [c for c in codes if c not in BY_CODE]
    if bad:
        parser.error(f"unknown states: {bad}")
    payload = extract_all(codes, keep=args.keep)
    print(f"{len(payload['spots'])} coastal spots in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
