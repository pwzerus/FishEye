"""Write app/knowledge/gear_photos.py from the photos picked by eye.

    python -m app.cli.gear_photos          # from backend/, after picking

Input, in gear_cache/ (git-ignored): candidates*.json, the search results
with their licence and creator (PD, CC0 or CC BY only, checked with
fish_id_commons.licence_ok), and picks.tsv, one line per gear item:
`<item id><TAB><file title>`. Only the metadata is kept. A Commons photo stays
on Wikimedia and is hot-linked with its credit; a Flickr photo (titled
`Flickr:<id>`) or a crop of a Commons one (`Crop:<name>`) lives in
frontend/public/gear-photos/<item>.jpg.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

from app.cli.fish_id_commons import licence_ok

CACHE = Path("gear_cache")
OUT = Path("app/knowledge/gear_photos.py")


def _plain(value: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    return re.sub(r"\s+", " ", text).strip()


# Where the file page names no author ("own work"), the uploader is the author.
AUTHOR_OVERRIDES = {"File:FishHooks.JPG": "Viridiflavus"}


def _author(artist_html: str, file: str = "") -> str:
    if file in AUTHOR_OVERRIDES:
        return AUTHOR_OVERRIDES[file]
    name = _plain(artist_html)
    name = re.sub(r"^(Photo|Photograph|Author|By)\s*:\s*", "", name, flags=re.I)
    name = re.sub(r"\(\s*talk\s*\)", "", name, flags=re.I)
    name = re.sub(r"^[a-z]{2}:[^:]+:", "", name)  # "fi:Käyttäjä:Jacofin" -> "Jacofin"
    name = name.strip(" ()")
    return (name[:77] + "…") if len(name) > 80 else (name or "Unknown author")


def build(cache: Path = CACHE) -> dict[str, dict]:
    # Every candidate seen in any search round, by file title.
    by_title: dict[str, dict] = {}
    for path in sorted(cache.glob("candidates*.json")):
        for found in json.loads(path.read_text(encoding="utf-8")).values():
            for c in found:
                by_title.setdefault(c["title"], c)
    photos: dict[str, dict] = {}
    for line in (cache / "picks.tsv").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        item, title = line.split("	")
        c = by_title[title]
        if not licence_ok(c["licence"]):
            raise SystemExit(f"{item}: {title} has licence {c['licence']!r}, not PD/CC0/CC BY")
        photos[item] = {
            "file": title,
            "url": c["thumb"].split("?")[0],
            "width": int(c["thumb_w"]),
            "height": int(c["thumb_h"]),
            "author": _author(c["artist_html"], title),
            "licence": c["licence"],
            "licence_url": c.get("licence_url") or None,
            "page": c["page_url"],
            "title": c.get("work_title"),
        }
    return photos


def render(photos: dict[str, dict]) -> str:
    lines = [
        '"""Gear photos picked by eye from Wikimedia Commons and Flickr (written by',
        'app/cli/gear_photos.py; edit gear_cache/picks.tsv and re-run rather than editing this',
        'file). Public domain, CC0 or CC BY only; each is shown with its author and licence',
        '(app/knowledge/gear.py)."""',
        "from app.knowledge.gear import GearPhoto",
        "",
        "PHOTOS: dict[str, GearPhoto] = {",
    ]
    for item in sorted(photos):
        p = photos[item]
        lines.append(f"    {item!r}: GearPhoto(")
        for key in ("file", "url", "width", "height", "author", "licence", "licence_url", "page", "title"):
            if key != "title" or p[key]:
                lines.append(f"        {key}={p[key]!r},")
        lines.append("    ),")
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    photos = build()
    OUT.write_text(render(photos), encoding="utf-8")
    print(f"{len(photos)} gear photos written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
