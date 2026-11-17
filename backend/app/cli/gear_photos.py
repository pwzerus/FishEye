"""Write app/knowledge/gear_photos.py from the photos picked by eye.

    python -m app.cli.gear_photos          # from backend/, after picking
    python -m app.cli.gear_photos --fetch  # also download any photo not kept yet

Input, in gear_cache/ (git-ignored): candidates*.json, the search results
with their licence and creator (PD, CC0 or CC BY only, checked with
fish_id_commons.licence_ok), and picks.tsv, one line per gear item:
`<item id><TAB><file title>`. Every photo lives in
frontend/public/gear-photos/<item>.jpg, with a 500px copy in /500, and is
shown with its credit. Commons photos were hot-linked until 2026-11-16, when
some tiles came up blank on a phone; `--fetch` copies the 960px Commons
thumbnail (one request a second, FishEye's User-Agent). A Flickr photo
(titled `Flickr:<id>`) or a crop of a Commons one (`Crop:<name>`) was put
there by hand.
"""
from __future__ import annotations

import html
import json
import re
import io
import sys
import time
from pathlib import Path

from app.cli.fish_id_commons import licence_ok

CACHE = Path("gear_cache")
OUT = Path("app/knowledge/gear_photos.py")
PUBLIC = Path("../frontend/public/gear-photos")
SMALL = 500  # the srcset's smaller copy (frontend lib/photoSizes.ts)


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
            "source": c["thumb"].split("?")[0],
            "url": f"/gear-photos/{item}.jpg",
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


def _save(data: bytes, item: str, public: Path) -> None:
    """Writes <item>.jpg as served (a PNG goes on white) and its 500px copy."""
    from PIL import Image

    image = Image.open(io.BytesIO(data))
    image.load()
    if image.format == "JPEG":
        (public / f"{item}.jpg").write_bytes(data)
    if image.mode != "RGB":
        rgba = image.convert("RGBA")
        image = Image.new("RGB", rgba.size, "white")
        image.paste(rgba, mask=rgba.getchannel("A"))
    if not (public / f"{item}.jpg").exists():
        image.save(public / f"{item}.jpg", quality=88, optimize=True)
    if image.width > SMALL:
        small = image.resize((SMALL, round(image.height * SMALL / image.width)), Image.LANCZOS)
        small.save(public / str(SMALL) / f"{item}.jpg", quality=85, optimize=True)


def fetch(photos: dict[str, dict], public: Path = PUBLIC) -> list[str]:
    """Downloads each photo not in `public` yet. Returns the items fetched."""
    import httpx

    from app.data_import.provenance import USER_AGENT

    (public / str(SMALL)).mkdir(parents=True, exist_ok=True)
    fetched = []
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60, follow_redirects=True) as client:
        for item, p in sorted(photos.items()):
            if (public / f"{item}.jpg").exists():
                continue
            if not p["source"].startswith("https://"):
                raise SystemExit(f"{item}: {p['file']} has to be put in {public} by hand")
            response = client.get(p["source"])
            response.raise_for_status()
            _save(response.content, item, public)
            fetched.append(item)
            time.sleep(1)
    return fetched


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    photos = build()
    if "--fetch" in args:
        print(f"{len(fetch(photos))} photos downloaded to {PUBLIC}")
    missing = [i for i in photos if not (PUBLIC / f"{i}.jpg").exists()]
    if PUBLIC.is_dir() and missing:
        raise SystemExit(f"not in {PUBLIC} yet (run with --fetch): {', '.join(missing)}")
    if PUBLIC.is_dir():
        # The file's own size: Commons can report 960 for an original that is smaller.
        from PIL import Image

        for item, p in photos.items():
            with Image.open(PUBLIC / f"{item}.jpg") as image:
                p["width"], p["height"] = image.size
    OUT.write_text(render(photos), encoding="utf-8", newline="\n")
    print(f"{len(photos)} gear photos written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
