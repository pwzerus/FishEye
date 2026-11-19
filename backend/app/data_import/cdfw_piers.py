"""California's public fishing piers and jetties, from CDFW's BIOS dataset
ds3090 "Public Piers and Jetties - R7" (CC BY 4.0; docs/data-sources.md).

They are the public piers of 14 CCR section 1.88: on them no fishing license
is needed, while every other rule (size and bag limits, report cards,
seasons) still applies. CDFW's notes say where next to a pier a license is
needed again, such as the rock wall where a jetty meets the shore; they are
kept as a short code the app words in each language.

The file is 38 KB and fetched once into cdfw_cache/ (data-sourcing rule 5):

    python -m app.data_import.cdfw_piers            # fetch if missing, then summarise

coastal_spots_db merges these with the OpenStreetMap spots: a pier mapped in
both becomes one spot with CDFW's name and OSM's hours, fee and lights.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

URL = (
    "https://data-cdfw.opendata.arcgis.com/api/download/v1/items/"
    "397f7591998d45b18bc2e2007b1e8d2a/geojson?layers=0"
)
PAGE = "https://data-cdfw.opendata.arcgis.com/datasets/CDFW::public-piers-and-jetties-r7-cdfw-ds3090"
CACHE = Path("cdfw_cache") / "ds3090.geojson"

# CDFW's notes, in the order they must be tried (the longer one first).
LICENSE_NOTES = (
    (re.compile(r"rock wall touching land and on jetty inside the harbor", re.I), "shore_wall_and_inner_jetty"),
    (re.compile(r"rock wall touching land", re.I), "shore_wall"),
    (re.compile(r"adjacent breakwater", re.I), "breakwater"),
    (re.compile(r"walking bridge", re.I), "footbridge"),
)
JETTY_NAME = re.compile(r"\b(jett(y|ies)|breakwater|rock wall|mole)\b", re.I)


def license_note(notes: str | None) -> str | None:
    """CDFW's note on where a license is still needed, as a code."""
    for pattern, code in LICENSE_NOTES:
        if notes and pattern.search(notes):
            return code
    return None


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def read(path: Path = CACHE) -> list[dict[str, Any]]:
    """The piers as coastal spots, in the shape coastal_spots.extract gives."""
    data = json.loads(Path(path).read_text("utf-8"))
    spots: list[dict[str, Any]] = []
    seen: set[str] = set()
    for f in data["features"]:
        p, g = f.get("properties") or {}, f.get("geometry")
        name = (p.get("pier") or "").strip()
        if not name or not g or g.get("type") != "Point":
            continue
        # Keyed by name: ArcGIS renumbers OBJECTID when a layer is republished.
        ref = "cdfw:" + _slug(name)
        if ref in seen:
            ref = f"{ref}-{p.get('OBJECTID')}"
        seen.add(ref)
        lng, lat = g["coordinates"][:2]
        spots.append({
            "ref": ref, "name": name[:160], "kind": "jetty" if JETTY_NAME.search(name) else "pier",
            "coast": "pacific", "state": "CA", "lat": round(lat, 6), "lng": round(lng, 6),
            "fishing_tagged": True, "no_license": True, "license_note": license_note(p.get("notes")),
            "fee": None, "opening_hours": None, "lit": False, "operator": None, "website": None,
        })
    return spots


def fetch(path: Path = CACHE) -> Path:
    """Download the GeoJSON once; a re-run reads the cached file."""
    if path.exists():
        return path
    import httpx

    from app.data_import.provenance import USER_AGENT

    path.parent.mkdir(parents=True, exist_ok=True)
    r = httpx.get(URL, headers={"User-Agent": USER_AGENT}, timeout=120, follow_redirects=True)
    r.raise_for_status()
    path.write_bytes(r.content)
    return path


if __name__ == "__main__":
    from collections import Counter

    spots = read(fetch())
    print(len(spots), "piers and jetties;", dict(Counter(s["kind"] for s in spots)),
          dict(Counter(s["license_note"] for s in spots)))
