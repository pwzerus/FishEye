"""Fetch the chosen Open Images photos from the dataset's public mirror.

    python -I oi_fetch.py <gear_cache dir>

Reads oi/meta.csv and oi/labels.json (oi_meta.py) and saves each photo,
shrunk to 640 px on its long side, as oi/img/<ImageID>.jpg. The mirror is
the dataset's own (open-images-dataset on S3, the one its downloader uses);
nothing is fetched from Flickr. One request at a time, at least 1 s apart,
with backoff on 429/5xx; photos already saved are skipped, so it can be
re-run. Rotation is left to the reader (meta.csv has it).
"""
import csv
import http.client
import io
import json
import ssl
import sys
import time
import urllib.error
from pathlib import Path

from PIL import Image

ROOT = Path(sys.argv[1]) / "oi"
IMG = ROOT / "img"
IMG.mkdir(exist_ok=True)
UA = {"User-Agent": "FishEye-gear-data/1.0 (feedback.fisheyefishing@gmail.com)"}
MIRROR = "https://open-images-dataset.s3.amazonaws.com/{subset}/{img}.jpg"
LONG_SIDE = 640
ORDER = {"gear": 0, "hard-negative": 1, "negative": 2}

labels = json.loads((ROOT / "labels.json").read_text("utf-8"))
meta = list(csv.DictReader(open(ROOT / "meta.csv", encoding="utf-8")))
meta.sort(key=lambda r: (ORDER[labels[r["ImageID"]]["kind"]], r["ImageID"]))
log = open(ROOT / "fetch.log", "a", encoding="utf-8")


def say(msg):
    print(msg, flush=True)
    log.write(msg + "\n")
    log.flush()


HOST = "open-images-dataset.s3.amazonaws.com"
CTX = ssl.create_default_context()  # once: on Windows each new one reads the cert store
conn = None


def get(path):
    """GET over one kept-alive connection, reopened when it drops."""
    global conn
    for _ in range(2):
        if conn is None:
            conn = http.client.HTTPSConnection(HOST, timeout=60, context=CTX)
        try:
            conn.request("GET", path, headers=UA)
            resp = conn.getresponse()
            body = resp.read()
        except (http.client.HTTPException, OSError):
            conn.close()
            conn = None
            continue
        if resp.status != 200:
            raise urllib.error.HTTPError(path, resp.status, resp.reason, resp.headers, None)
        return body
    raise ConnectionError(f"{path}: connection kept dropping")


# Photos the mirror doesn't have (about a third: it holds the 1.9M photos
# with boxes, not all 9M) are listed in fetch.log; don't ask again.
gone = {line.split(":")[0] for line in (ROOT / "fetch.log").read_text("utf-8").splitlines()
        if "HTTP 404" in line} if (ROOT / "fetch.log").exists() else set()
done = failed = skipped = 0
last = 0.0
for n, rec in enumerate(meta, 1):
    img = rec["ImageID"]
    out = IMG / f"{img}.jpg"
    if out.exists() or img in gone:
        skipped += 1
        continue
    path = f"/{rec['Subset']}/{img}.jpg"
    for attempt in range(4):
        wait = 1.0 - (time.monotonic() - last)
        if wait > 0:
            time.sleep(wait)
        last = time.monotonic()
        try:
            data = get(path)
            photo = Image.open(io.BytesIO(data))
            photo.load()
            photo = photo.convert("RGB")
            photo.thumbnail((LONG_SIDE, LONG_SIDE), Image.Resampling.LANCZOS)
            photo.save(out, "JPEG", quality=90)
            done += 1
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                say(f"{img}: HTTP {e.code}, backing off")
                time.sleep(30 * (attempt + 1))
                continue
            say(f"{img}: HTTP {e.code}, skipped")
            failed += 1
            break
        except Exception as e:  # network hiccup or a broken file
            say(f"{img}: {type(e).__name__}: {e}")
            time.sleep(5)
    else:
        failed += 1
    if n % 100 == 0:
        say(f"{n}/{len(meta)}: saved {done}, failed {failed}, already there {skipped}")
say(f"finished: saved {done}, failed {failed}, already there {skipped}, of {len(meta)}")
