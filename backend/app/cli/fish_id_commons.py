"""Fish photos from Wikimedia Commons, for the photo check (services/fish_id.py).

    python -m app.cli.fish_id_commons --steelhead     # steelhead, into the training and test sets
    python -m app.cli.fish_id_commons --test-set      # fishid_cache/commons/: a second test set
    python -m app.cli.fish_id_commons --share         # half of it, by photographer, to training

Two uses:

- **Steelhead.** A steelhead is a rainbow trout that went to sea (or to a
  Great Lake) and came back: the same species, so no species search can
  find its photos. Commons has many that their uploader calls steelhead,
  most from the US Fish and Wildlife Service and NOAA (public domain). They
  are split by who made them, so no photographer is in both: about a third
  go to the test set, the rest to training. Most of what a "steelhead"
  search finds is not a photo of one (Steelhead Falls, river views, trail
  signs, maps, dinner plates, engravings): on 2026-11-06 the 177 found were
  checked by eye on contact sheets and 30 kept. BioCLIP can't do this
  sorting itself: it read a map whose legend says "steelhead" as 98% fish.
- **A second test set** of every fish class, from each species' Commons
  category: photos from anglers, agencies and aquariums rather than
  iNaturalist's, to see how the check does on pictures like the ones people
  find online. BioCLIP's training data included some Commons photos (via the
  Encyclopedia of Life), so this set flatters the zero-shot model; it is fair
  between heads. `--share` then moves about half of it, chosen by
  photographer, into training (2026-11-06: web photos are what people try,
  and several new fish have few open iNaturalist photos); the half left is
  still never fitted on, and no photographer is on both sides.

Licences: public domain (including "No restrictions"), CC0 and CC BY of any
version only. No share-alike (a fitted head is an adaptation, and BY-SA
would bind it), no NC, no ND (the data-sourcing skill). Each photo's page,
licence and creator go in the manifest; a head fitted on them credits
them in TRAINING_CREDITS.json like the iNaturalist ones.

Polite: one request at a time, a second apart, FishEye's User-Agent, the
500 px thumbnail Commons makes anyway.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

from app.data_import.provenance import USER_AGENT
from app.services.fish_id_classes import CLASSES, NOT_FISH, SAME_FISH

API = "https://commons.wikimedia.org/w/api.php"
CACHE = Path("fishid_cache")
PAUSE_S = 1.0

# LicenseShortName values allowed, after lower-casing.
_OPEN = re.compile(r"^(public domain|pd[- ].*|no restrictions|cc0.*|cc[- ]by[- ](1\.0|2\.0|2\.5|3\.0|4\.0)(\s.*)?|cc by( \d\.\d)?|attribution)$")
_CLOSED = re.compile(r"\b(sa|nc|nd|share ?alike|non-?commercial|no ?deriv)", re.I)
# Not a photo of a fish to identify: young fish, eggs, scenery, gear,
# drawings, maps, dishes, specimens in jars.
_NOT_A_CATCH = re.compile(
    r"smolt|juvenile|fry\b|eggs?\b|parr\b|fingerling|alevin|hatchery tank|raceway|ladder|dam\b|weir|map\b|range|"
    r"distribution|drawing|illustration|plate\b|diagram|logo|stamp|poster|coin|sushi|fillet|recipe|dish|cooked|"
    r"market|skeleton|jar\b|specimen|museum|sign\b|truck|boat\b|people|crew|volunteer",
    re.I,
)


def licence_ok(short: str | None) -> bool:
    s = (short or "").strip().lower()
    return bool(s) and not _CLOSED.search(s) and bool(_OPEN.match(s))


def _plain(value: str | None) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


class Commons:
    def __init__(self) -> None:
        import httpx

        self.client = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60, follow_redirects=True)

    def get(self, url: str, **params: Any):
        time.sleep(PAUSE_S)
        for attempt in range(4):
            resp = self.client.get(url, params=params or None)
            if resp.status_code not in (429, 500, 502, 503, 504):
                resp.raise_for_status()
                return resp
            time.sleep(10 * (attempt + 1))
        resp.raise_for_status()
        return resp

    def files(self, **generator: Any) -> list[dict[str, Any]]:
        """Bitmap files with their licence, creator and a 500 px thumbnail."""
        out: list[dict[str, Any]] = []
        params = {
            "action": "query", "format": "json", "prop": "imageinfo",
            "iiprop": "url|extmetadata|mime", "iiurlwidth": 500,
            "iiextmetadatafilter": "LicenseShortName|Artist|ImageDescription|ObjectName",
            **generator,
        }
        cont: dict[str, Any] = {}
        for _ in range(10):
            data = self.get(API, **params, **cont).json()
            for page in (data.get("query") or {}).get("pages", {}).values():
                info = (page.get("imageinfo") or [{}])[0]
                if info.get("mime") not in ("image/jpeg", "image/png"):
                    continue
                md = info.get("extmetadata") or {}
                out.append({
                    "pageid": page["pageid"],
                    "title": page["title"],
                    "thumb": info.get("thumburl"),
                    "page_url": info.get("descriptionurl"),
                    "licence": _plain((md.get("LicenseShortName") or {}).get("value")),
                    "creator": _plain((md.get("Artist") or {}).get("value"))[:120],
                    "text": " ".join(_plain((md.get(k) or {}).get("value")) for k in ("ObjectName", "ImageDescription"))[:600],
                })
            if "continue" not in data:
                break
            cont = data["continue"]
        return out


def _usable(f: dict[str, Any]) -> bool:
    words = f"{f['title']} {f['text']}"
    return bool(f["thumb"]) and licence_ok(f["licence"]) and not _NOT_A_CATCH.search(words)


def _save(commons: Commons, f: dict[str, Any], slug: str, cache: Path, manifest: dict[str, Any]) -> bool:
    key = f"c{f['pageid']}"
    if any(p["gbif_id"] == key for p in manifest["photos"]):
        return False
    folder = cache / "photos" / slug
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{key}.jpg"
    try:
        target.write_bytes(commons.get(f["thumb"]).content)
    except Exception as exc:  # noqa: BLE001 - one bad photo must not stop the set
        print(f"  {slug}: {f['thumb']}: {exc}", file=sys.stderr)
        return False
    manifest["photos"].append({
        "gbif_id": key,
        "observation": f["page_url"] or f"https://commons.wikimedia.org/?curid={f['pageid']}",
        "url": f["thumb"],
        "licence": f["licence"],
        "creator": f["creator"],
        "slug": slug,
        "file": str(target.relative_to(cache)).replace("\\", "/"),
        "source": "wikimedia-commons",
    })
    return True


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text("utf-8")) if path.exists() else {"photos": []}


def _write(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")


def steelhead(test_share: float = 0.34) -> None:
    commons = Commons()
    found: dict[int, dict[str, Any]] = {}
    for query in ("steelhead", "steelhead trout", "steelhead fish", "Oncorhynchus mykiss steelhead"):
        for f in commons.files(generator="search", gsrsearch=f"{query} filetype:bitmap", gsrnamespace=6, gsrlimit=50):
            if "steelhead" in f"{f['title']} {f['text']}".lower() and _usable(f):
                found[f["pageid"]] = f
    print(f"steelhead: {len(found)} usable Commons photos")
    # Split by creator: every photo of one photographer on one side.
    test_m, train_m = _load(CACHE / "manifest.json"), _load(CACHE / "train" / "manifest.json")
    added = {"test": 0, "train": 0}
    for f in sorted(found.values(), key=lambda f: f["pageid"]):
        who = re.sub(r"\W+", " ", f["creator"].lower()).strip() or f"page {f['pageid']}"
        side = "test" if int(hashlib.sha1(who.encode()).hexdigest(), 16) % 100 < test_share * 100 else "train"
        cache, manifest = (CACHE, test_m) if side == "test" else (CACHE / "train", train_m)
        added[side] += _save(commons, f, "steelhead", cache, manifest)
    _write(CACHE / "manifest.json", test_m)
    _write(CACHE / "train" / "manifest.json", train_m)
    print(f"steelhead: {added['test']} test, {added['train']} training photos added")


def test_set(per_class: int = 15) -> None:
    commons = Commons()
    cache = CACHE / "commons"
    manifest = _load(cache / "manifest.json")
    for c in CLASSES:
        if c.kind == NOT_FISH or c.slug in SAME_FISH:
            continue
        have = sum(p["slug"] == c.slug for p in manifest["photos"])
        if have >= per_class:
            continue
        files = commons.files(generator="categorymembers", gcmtitle=f"Category:{c.scientific}", gcmtype="file", gcmlimit=200)
        files = [f for f in files if _usable(f)]
        n = 0
        for f in files:
            if have + n >= per_class:
                break
            n += _save(commons, f, c.slug, cache, manifest)
        _write(cache / "manifest.json", manifest)
        print(f"  {c.slug}: {have + n} photos")
    # Steelhead's test photos are in the main test set (split by creator).
    print(f"{len(manifest['photos'])} photos in {cache / 'manifest.json'}")


def _side(photo: dict[str, Any], test_share: float) -> str:
    who = re.sub(r"\W+", " ", photo.get("creator", "").lower()).strip() or photo["gbif_id"]
    return "test" if int(hashlib.sha1(who.encode()).hexdigest(), 16) % 100 < test_share * 100 else "train"


def share(test_share: float = 0.5) -> None:
    """Move the training side of the Commons set (by photographer) into
    fishid_cache/train/, files and manifest rows both."""
    src, dst = CACHE / "commons", CACHE / "train"
    commons, train = _load(src / "manifest.json"), _load(dst / "manifest.json")
    have = {p["gbif_id"] for p in train["photos"]}
    kept, moved = [], 0
    for p in commons["photos"]:
        if _side(p, test_share) == "test":
            kept.append(p)
            continue
        if p["gbif_id"] not in have:
            target = dst / p["file"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((src / p["file"]).read_bytes())
            train["photos"].append(p)
            moved += 1
    commons["photos"] = kept
    _write(src / "manifest.json", commons)
    _write(dst / "manifest.json", train)
    print(f"{moved} Commons photos moved to training; {len(kept)} stay in the Commons test set")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--steelhead", action="store_true")
    parser.add_argument("--test-set", action="store_true")
    parser.add_argument("--per-class", type=int, default=15)
    parser.add_argument("--share", action="store_true", help="move half of the Commons set, by photographer, to training")
    args = parser.parse_args(argv)
    if args.steelhead:
        steelhead()
    if args.test_set:
        test_set(args.per_class)
    if args.share:
        share()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
