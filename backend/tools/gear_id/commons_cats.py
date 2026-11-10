"""Gear photos from Wikimedia Commons categories (more than search finds).

    cd backend && .venv/Scripts/python -I gear_cache/scripts/commons_cats.py

Lists each gear category and its direct subcategories (skipping heraldry,
archaeology, museums and the like), keeps bitmap files whose licence passes
fish_id_commons.licence_ok (public domain, CC0, CC BY; no SA/NC/ND), and
saves a 500 px thumbnail of each as gear_cache/commons_cat/img/<pageid>.jpg.
Metadata (title, page, licence, creator, category) goes to
gear_cache/commons_cat/files.json. One request at a time, 1 s apart.
"""
import json
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
from app.cli.fish_id_commons import API, Commons, licence_ok  # noqa: E402

OUT = BACKEND / "gear_cache" / "commons_cat"
IMG = OUT / "img"
IMG.mkdir(parents=True, exist_ok=True)
# Category -> the coarse kind its files are, before checking them by eye.
ROOTS = {
    "Fishing lure": "lure", "Fishing reels": "reel", "Fishing rods": "rod", "Fishing floats": "float",
    "Fishing hooks": "hook", "Fishing line": "line", "Fishing weights": "sinker", "Fishing bait": "bait",
    "Ice fishing equipment": "ice", "Fishing swivels": "swivel",
}
SKIP = re.compile(r"heraldry|birds with|shell fish|bone fish|bronze|museo|museum|egizio|KIT|illustration|"
                  r"in art|stamps|vending|diggers|shops|livewell|nets?\b|vessels|traps|by location", re.I)

commons = Commons()
meta_path = OUT / "files.json"
files = json.loads(meta_path.read_text("utf-8")) if meta_path.exists() else {}


def subcats(cat):
    data = commons.get(API, action="query", format="json", list="categorymembers", cmtitle=f"Category:{cat}",
                       cmtype="subcat", cmlimit=200).json()
    return [m["title"][9:] for m in data["query"]["categorymembers"]]


todo = []
for root, kind in ROOTS.items():
    todo.append((root, kind))
    for sub in subcats(root):
        if sub in ROOTS or SKIP.search(sub):
            continue
        todo.append((sub, kind))
print(f"{len(todo)} categories", flush=True)

for cat, kind in todo:
    found = commons.files(generator="categorymembers", gcmtitle=f"Category:{cat}", gcmtype="file", gcmlimit=50)
    kept = 0
    for f in found:
        key = str(f["pageid"])
        if key in files or not f["thumb"] or not licence_ok(f["licence"]):
            continue
        files[key] = {**f, "kind": kind, "category": cat}
        kept += 1
    print(f"  {cat}: {len(found)} files, {kept} new with an open licence", flush=True)
    meta_path.write_text(json.dumps(files, indent=1), encoding="utf-8")

saved = failed = 0
for key, f in files.items():
    out = IMG / f"{key}.jpg"
    if out.exists():
        continue
    time.sleep(1.0)
    try:
        r = commons.client.get(f["thumb"])
        r.raise_for_status()
        out.write_bytes(r.content)
        saved += 1
    except Exception as e:  # noqa: BLE001
        f["error"] = str(e)[:120]
        failed += 1
    if (saved + failed) % 100 == 0:
        print(f"  thumbnails: {saved} saved, {failed} failed", flush=True)
meta_path.write_text(json.dumps(files, indent=1), encoding="utf-8")
print(f"done: {len(files)} files, {saved} thumbnails saved now, {failed} failed", flush=True)
