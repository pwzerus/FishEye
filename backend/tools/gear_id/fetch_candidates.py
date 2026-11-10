"""Download the gear photos scan_catalogs.py found, for checking by eye.

    python -I fetch_candidates.py <gear_cache dir> <batch name> <source,source,...>

Reads <gear_cache>/open2/{pd12m,yfcc,smithsonian,commoncatalog}.jsonl and
keeps the close-up candidates:
  - any photo named as a gear item, except one named only as a life jacket
    (thousands of boating scenes; the class has photos enough);
  - a photo named only by a kind of gear ("fishing reel", "lures"), except
    PD12M's "a man holding a fishing rod" captions: 3,000 scenes and
    paintings with a rod far off, not what a camera user shows the app.
A Flickr photo in both YFCC and CommonCatalog is fetched once, from YFCC's
copy on AWS (smaller and quicker).

Each photo is saved as <gear_cache>/open2/img/<source>/<id>.jpg, at most 640
px on its long side (as the other training photos), the original never
written to disk. Writes open2/candidates.json (licence, author, page, the
words that found it) and work/check-open.json (the photos in sheet order,
for sheet.py and handcheck.py apply). Re-running skips photos already saved.
Batches (e.g. "open1" for pd12m,yfcc,smithsonian, "open2" for commoncatalog)
keep each check list's numbering fixed while another source still scans:
open2/candidates-<batch>.json and work/check-<batch>.json.
"""
import concurrent.futures as cf
import io
import json
import re
import sys
import threading
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from spot_check import bucket_of  # noqa: E402

UA = "FishEye-dataset-scan/1.0 (feedback.fisheyefishing@gmail.com)"
ROOT = Path(sys.argv[1])
BATCH = sys.argv[2]
SOURCES = sys.argv[3].split(",")
OPEN = ROOT / "open2"
IMG = OPEN / "img"


def keep(src, row):
    items = set(row["m"]["items"])
    if items:
        return items != {"tool-lifejacket"}
    groups = set(row["m"]["groups"])
    return not (src == "pd12m" and groups <= {"rod", "gear"})


def safe(s):
    return re.sub(r"[^\w.-]", "_", str(s))[:80]


def fetch(url, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception:  # noqa: BLE001 - retried, then raised
            if k == tries - 1:
                raise
            time.sleep(3 * (k + 1))


def save_small(data, path):
    img = Image.open(io.BytesIO(data))
    img.load()
    img = img.convert("RGB")
    img.thumbnail((640, 640))
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    path.write_bytes(buf.getvalue())
    return len(data), buf.tell()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    rows = []
    yfcc_ids = set()
    # photos already in another batch's list keep their place there
    earlier = set()
    for c in OPEN.glob("candidates-*.json"):
        if c.name != f"candidates-{BATCH}.json":
            earlier |= {x["id"] for x in json.loads(c.read_text("utf-8"))}
    for src in ("yfcc", "pd12m", "smithsonian", "commoncatalog"):
        p = OPEN / f"{src}.jsonl"
        if not p.exists():
            continue
        if src not in SOURCES and src != "yfcc":
            continue
        for line in p.open(encoding="utf-8"):
            r = json.loads(line)
            if not keep(src, r):
                continue
            if src == "yfcc":
                yfcc_ids.add(str(r["id"]))
            if src == "commoncatalog" and str(r["id"]) in yfcc_ids:
                continue
            if src in SOURCES and f"open:{src}:{r['id']}" not in earlier:
                rows.append((src, r))
    print("candidates:", Counter(s for s, _ in rows), flush=True)

    stats = defaultdict(lambda: {"n": 0, "downloaded": 0, "stored": 0, "failed": 0})
    lock = threading.Lock()
    cc = None
    if any(s == "commoncatalog" for s, _ in rows):
        from cc_images import CCReader
        cc = CCReader()
    si_last = [0.0]

    def work(item):
        src, r = item
        path = IMG / src / f"{safe(r['id'])}.jpg"
        if path.exists():
            return src, path, None
        if src == "smithsonian":
            with lock:  # one at a time, a second apart, for a museum's image server
                wait = 1.0 - (time.time() - si_last[0])
                if wait > 0:
                    time.sleep(wait)
                si_last[0] = time.time()
                url = r["images"][0]["url"]
                data = fetch(url + ("&" if "?" in url else "?") + "max=1024")
        elif src == "commoncatalog":
            data = cc.image(r["file"], r["row"])
        else:
            data = fetch(r["image"])
        return src, path, save_small(data, path)

    t0 = time.time()
    done = 0
    pools = {"smithsonian": 1, "commoncatalog": 6, "pd12m": 4, "yfcc": 4}
    results = {}
    with cf.ThreadPoolExecutor(sum(pools.values())) as ex:
        futs = {ex.submit(work, it): it for it in rows}
        for f in cf.as_completed(futs):
            src, r = futs[f]
            done += 1
            try:
                _, path, sizes = f.result()
                results[(src, str(r["id"]))] = path
                if sizes:
                    s = stats[src]
                    s["n"] += 1
                    s["downloaded"] += sizes[0]
                    s["stored"] += sizes[1]
            except Exception as e:  # noqa: BLE001 - counted; the photo is left out
                stats[src]["failed"] += 1
                print("  failed", src, r["id"], str(e)[:120], flush=True)
            if done % 100 == 0 or done == len(rows):
                print(f"  {done}/{len(rows)} in {(time.time() - t0) / 60:.1f} min", flush=True)

    cands, check = [], []
    for src, r in sorted(rows, key=lambda x: (bucket_of(x[1])[0], x[0], str(x[1]["id"]))):
        path = results.get((src, str(r["id"])))
        if not path:
            continue
        key = f"open:{src}:{r['id']}"
        cands.append({"id": key, "source": src, "path": str(path), "licence": r.get("licence"),
                      "author": r.get("author") or r.get("unit") or r.get("src"),
                      "page": r.get("page") or r.get("image"), "words": r["m"]["words"],
                      "text": r.get("text", "")[:300]})
        check.append({"id": key, "path": str(path), "rotate": 0, "note": src[0].upper()})
    (OPEN / f"candidates-{BATCH}.json").write_text(json.dumps(cands, ensure_ascii=False, indent=0), "utf-8")
    (ROOT / "work" / f"check-{BATCH}.json").write_text(json.dumps(check, indent=0), "utf-8")
    (OPEN / f"fetch_sizes-{BATCH}.json").write_text(json.dumps(stats, indent=1), "utf-8")
    print("saved:", len(cands), dict(stats), flush=True)


if __name__ == "__main__":
    main()
