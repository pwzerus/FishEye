"""Spot check for scan_catalogs.py: how many found photos really show the gear,
and how much disk the photos would take.

    python -I spot_check.py <scan dir> [per_bucket] [seed]

Takes a random sample of matches from each kind of gear (pooled across the
sources, at least a few from each source that has any), downloads just
those photos, keeps each at most 640 px on its long side (as training
stores them), and draws numbered contact sheets <scan dir>/check/<bucket>-NN.jpg
for checking by eye. Writes <scan dir>/check/sample.json (what each tile
is) and <scan dir>/check/sizes.json (bytes as downloaded and as stored,
per source).
"""
import io
import json
import random
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

UA = "FishEye-dataset-scan/1.0 (feedback.fisheyefishing@gmail.com)"
# CommonCatalog's images sit inside its parquet files (about 130 MB a row
# group), so its matches aren't sampled here: they are the same kind of
# Flickr text as yfcc, whose rate stands in for them.
SOURCES = ["pd12m", "yfcc", "smithsonian"]
SHORT = {"pd12m": "P", "yfcc": "F", "smithsonian": "S", "commoncatalog": "C"}
BUCKET = {
    "rod-spinning": "rod", "rod-baitcasting": "rod", "rod-fly": "rod", "rod-ice": "rod", "pole-cane": "rod",
    "combo-spincast": "rod", "reel-spinning": "reel", "reel-baitcasting": "reel", "line-mono": "line",
    "line-braid": "line", "hook-j": "hook", "hook-circle": "hook", "hook-treble": "hook",
    "sinker-split-shot": "sinker", "sinker-egg": "sinker", "sinker-bank": "sinker", "bobber": "float",
    "float-slip": "float", "swivel": "terminal", "leader-wire": "terminal", "lure-spoon": "spoon",
    "fly-dry": "fly", "tool-tackle-box": "tackle-box",
}


def bucket_of(row):
    items = row["m"]["items"]
    if items:
        strong = [i for i, s in items.items() if s == "strong"]
        item = sorted(strong or items)[0]
        if item in BUCKET:
            return BUCKET[item], item
        if item.startswith("lure-") or item == "jig-head":
            return "lure", item
        if item.startswith("bait-"):
            return "bait", item
        return "tools", item
    g = sorted(row["m"]["groups"])[0]
    return "group-only", "g:" + g


def image_url(source, row):
    if source == "smithsonian":
        u = row["images"][0]["url"]
        return u + ("&" if "?" in u else "?") + "max=1024"
    if source == "commoncatalog":
        k = row.get("key")
        return f"https://multimedia-commons.s3.amazonaws.com/data/images/{k[:3]}/{k[3:6]}/{k}.jpg" if k else None
    return row.get("image")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    scan = Path(sys.argv[1])
    per = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 11)
    out = scan / "check"
    (out / "img").mkdir(parents=True, exist_ok=True)

    pools = defaultdict(lambda: defaultdict(list))
    for src in SOURCES:
        p = scan / f"{src}.jsonl"
        if not p.exists():
            continue
        for line in p.open(encoding="utf-8"):
            row = json.loads(line)
            b, item = bucket_of(row)
            pools[b][src].append((item, row))

    sample, sizes = [], defaultdict(lambda: {"n": 0, "downloaded": 0, "stored": 0, "failed": 0})
    last = defaultdict(float)
    for b in sorted(pools):
        by_src = pools[b]
        total = sum(len(v) for v in by_src.values())
        picks = []
        for src, rows in by_src.items():
            k = max(min(4, len(rows)), round(per * len(rows) / total))
            picks += [(src, it, r) for it, r in rng.sample(rows, min(k, len(rows)))]
        rng.shuffle(picks)
        picks = picks[:per]
        for n, (src, item, row) in enumerate(picks, 1):
            url = image_url(src, row)
            if not url:
                continue
            host = url.split("/")[2]
            wait = (1.0 if "si.edu" in host else 0.2) - (time.time() - last[host])
            if wait > 0:
                time.sleep(wait)
            last[host] = time.time()
            try:
                data = fetch(url)
                img = Image.open(io.BytesIO(data)).convert("RGB")
                img.thumbnail((640, 640))
                buf = io.BytesIO()
                img.save(buf, "JPEG", quality=88)
                path = out / "img" / f"{b}-{n:02d}-{SHORT[src]}.jpg"
                path.write_bytes(buf.getvalue())
            except Exception as e:  # noqa: BLE001 - counted, the tile is left out
                sizes[src]["failed"] += 1
                print("  failed", src, url, e)
                continue
            s = sizes[src]
            s["n"] += 1
            s["downloaded"] += len(data)
            s["stored"] += buf.tell()
            sample.append({"bucket": b, "tile": n, "source": src, "item": item, "id": row.get("id"),
                           "path": str(path), "text": row.get("text", "")[:200], "words": row["m"]["words"]})
        print(f"{b}: {total} found, {len(picks)} sampled", flush=True)

    (out / "sample.json").write_text(json.dumps(sample, ensure_ascii=False, indent=1), "utf-8")
    (out / "sizes.json").write_text(json.dumps(sizes, indent=1), "utf-8")

    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    cols, rows_, tile, cap = 6, 5, 200, 18
    for b in sorted({s["bucket"] for s in sample}):
        tiles = [s for s in sample if s["bucket"] == b]
        sheet = Image.new("RGB", (cols * tile, rows_ * (tile + cap)), "white")
        d = ImageDraw.Draw(sheet)
        for k, s in enumerate(tiles[:cols * rows_]):
            img = Image.open(s["path"])
            img.thumbnail((tile - 4, tile - 4))
            x, y = (k % cols) * tile, (k // cols) * (tile + cap)
            sheet.paste(img, (x + (tile - img.width) // 2, y + (tile - img.height) // 2))
            d.rectangle([x, y + tile, x + tile, y + tile + cap], fill="black")
            d.text((x + 3, y + tile + 1), f"{s['tile']}{SHORT[s['source']]} {s['item']}"[:26], fill="yellow", font=font)
        sheet.save(out / f"{b}.jpg", quality=85)
        print(out / f"{b}.jpg")


if __name__ == "__main__":
    main()
