"""Build the county outlines the app finds a catch's county with.

Source: US Census Bureau cartographic boundary file, counties, 1:500,000
(cb_2024_us_county_500k; public domain, docs/data-sources.md). Download the
shapefile zip once into census_cache/ and unzip it there:

    https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_county_500k.zip

Then:

    python -m app.data_import.census_counties

writes app/data/us_counties.json.gz: per county its GEOID, name ("Harris
County", "Orleans Parish"), state and outline, simplified to ~100 m and
rounded to 4 decimals (~10 m) so it ships with the code (a few MB).

The shapefile is read here directly (polygons and a dBASE table are simple
formats), so the build needs nothing beyond the standard library.
"""
from __future__ import annotations

import argparse
import gzip
import json
import struct
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parents[2]
SOURCE = BACKEND / "census_cache" / "cb_2024_us_county_500k"
OUT = BACKEND / "app" / "data" / "us_counties.json.gz"
TOLERANCE = 0.001  # degrees, ~100 m


def read_dbf(path: Path) -> list[dict[str, str]]:
    data = path.read_bytes()
    n, header_len, record_len = struct.unpack("<IHH", data[4:12])
    fields, pos = [], 32
    while data[pos] != 0x0D:
        name = data[pos : pos + 11].split(b"\0")[0].decode("ascii")
        fields.append((name, data[pos + 16]))
        pos += 32
    rows = []
    for i in range(n):
        rec = data[header_len + i * record_len : header_len + (i + 1) * record_len]
        row, off = {}, 1  # first byte: deletion flag
        for name, length in fields:
            row[name] = rec[off : off + length].decode("utf-8", "replace").strip()
            off += length
        rows.append(row)
    return rows


def read_shp(path: Path) -> list[list[list[tuple[float, float]]]]:
    """Each record's rings (outer and holes alike, as the even-odd rule
    treats them)."""
    data = path.read_bytes()
    out, pos = [], 100
    while pos < len(data):
        _, length = struct.unpack(">ii", data[pos : pos + 8])
        body = data[pos + 8 : pos + 8 + length * 2]
        pos += 8 + length * 2
        if struct.unpack("<i", body[:4])[0] == 0:
            out.append([])
            continue
        n_parts, n_points = struct.unpack("<ii", body[36:44])
        parts = list(struct.unpack(f"<{n_parts}i", body[44 : 44 + 4 * n_parts])) + [n_points]
        start = 44 + 4 * n_parts
        pts = struct.unpack(f"<{2 * n_points}d", body[start : start + 16 * n_points])
        out.append([[(pts[2 * k], pts[2 * k + 1]) for k in range(parts[p], parts[p + 1])] for p in range(n_parts)])
    return out


def simplify(ring: list[tuple[float, float]], tol: float = TOLERANCE) -> list[tuple[float, float]]:
    """Douglas-Peucker, iteratively; a ring keeps at least 4 points."""
    if len(ring) <= 4:
        return ring
    keep = [False] * len(ring)
    keep[0] = keep[-1] = True
    stack = [(0, len(ring) - 1)]
    while stack:
        a, b = stack.pop()
        (ax, ay), (bx, by) = ring[a], ring[b]
        dx, dy = bx - ax, by - ay
        norm = (dx * dx + dy * dy) ** 0.5
        best, best_i = -1.0, -1
        for i in range(a + 1, b):
            px, py = ring[i]
            d = abs(dy * px - dx * py + bx * ay - by * ax) / norm if norm else ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
            if d > best:
                best, best_i = d, i
        if best > tol:
            keep[best_i] = True
            stack += [(a, best_i), (best_i, b)]
    out = [p for p, k in zip(ring, keep) if k]
    return out if len(out) >= 4 else ring


def build(source: Path = SOURCE) -> list[dict[str, Any]]:
    rows = read_dbf(source.with_suffix(".dbf"))
    shapes = read_shp(source.with_suffix(".shp"))
    counties = []
    for row, rings in zip(rows, shapes):
        if not rings:
            continue
        rings = [[(round(x, 4), round(y, 4)) for x, y in simplify(r)] for r in rings]
        counties.append({
            "geoid": row["GEOID"],
            "name": row["NAMELSAD"],
            "state": row["STUSPS"],
            "rings": rings,
        })
    counties.sort(key=lambda c: c["geoid"])
    return counties


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--source", type=Path, default=SOURCE, help="shapefile path without extension")
    p.add_argument("--out", type=Path, default=OUT)
    args = p.parse_args(argv)
    counties = build(args.source)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(args.out, "wt", encoding="utf-8") as f:
        json.dump({"source": "US Census Bureau, cb_2024_us_county_500k (public domain)", "counties": counties}, f, separators=(",", ":"))
    points = sum(len(r) for c in counties for r in c["rings"])
    print(f"{len(counties)} counties, {points} points -> {args.out} ({args.out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
