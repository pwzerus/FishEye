"""Fish photos from Open Images (images CC BY 2.0, labels CC BY 4.0) for an
"is there a fish" gate that learns nothing from iNaturalist, 2026-11-19.

    python -I tools/fish_id_b25/oi_fish.py labels   (stream the human-verified labels, keep fish yes)
    python -I tools/fish_id_b25/oi_fish.py meta     (stream the image lists: CC BY 2.0 rows, credits)
    python -I tools/fish_id_b25/oi_fish.py fetch    (the photos, from the dataset's own S3 mirror)

Writes F:/tmp/fish_gate/oi_fish/{labels.csv,meta.csv,img/<ImageID>.jpg}. As
tools/gear_id/oi_meta.py and oi_fetch.py do for gear: human-verified "yes"
labels only, CC BY 2.0 rows only, nothing fetched from Flickr, one request at
a time at least 1 s apart, 640 px on the long side.
"""
import csv
import hashlib
import io
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

OUT = Path("F:/tmp/fish_gate/oi_fish")
IMG = OUT / "img"
UA = {"User-Agent": "FishEye-fish-gate/1.0 (feedback.fisheyefishing@gmail.com)"}
FISH = {"/m/0ch_cf": "fish", "/m/03fj2": "goldfish", "/m/0by6g": "shark", "/m/0nybt": "seahorse"}
LABELS = {
    "train": "https://storage.googleapis.com/openimages/v6/oidv6-train-annotations-human-imagelabels.csv",
    "validation": "https://storage.googleapis.com/openimages/v5/validation-annotations-human-imagelabels.csv",
    "test": "https://storage.googleapis.com/openimages/v5/test-annotations-human-imagelabels.csv",
}
LISTS = {
    "train": "https://storage.googleapis.com/openimages/v6/oidv6-train-images-with-labels-with-rotation.csv",
    "validation": "https://storage.googleapis.com/openimages/2018_04/validation/validation-images-with-rotation.csv",
    "test": "https://storage.googleapis.com/openimages/2018_04/test/test-images-with-rotation.csv",
}
CC_BY = "https://creativecommons.org/licenses/by/2.0/"
MIRROR = "https://open-images-dataset.s3.amazonaws.com/{subset}/{img}.jpg"
KEEP = 4000  # photos to fetch, a fixed hash order so a rerun picks the same


RAW = OUT / "raw"  # the big CSVs, downloaded with resume (curl -C -), deleted after "meta"


def stream(url):
    """The local copy when there is one (downloaded with resume: the big files
    reset mid-stream), else the URL itself."""
    local = RAW / url.rsplit("/", 1)[1]
    if local.exists():
        return open(local, encoding="utf-8", newline="")
    req = urllib.request.Request(url, headers=UA)
    return io.TextIOWrapper(urllib.request.urlopen(req, timeout=120), encoding="utf-8")


def labels():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for subset, url in LABELS.items():
        n = 0
        for r in csv.DictReader(stream(url)):
            if r["LabelName"] in FISH and float(r["Confidence"]) >= 0.5:
                rows.append((r["ImageID"], subset, FISH[r["LabelName"]]))
                n += 1
        print(subset, n, "fish labels", flush=True)
    with open(OUT / "labels.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)
    print("LABELS_DONE", len({r[0] for r in rows}), flush=True)


def meta():
    want = {}
    for img, subset, label in csv.reader(open(OUT / "labels.csv", encoding="utf-8")):
        want.setdefault(img, (subset, set()))[1].add(label)
    keep, other = [], 0
    for subset, url in LISTS.items():
        for r in csv.DictReader(stream(url)):
            if r["ImageID"] not in want:
                continue
            if r["License"] != CC_BY:
                other += 1
                continue
            keep.append({"ImageID": r["ImageID"], "Subset": subset, "Labels": "+".join(sorted(want[r["ImageID"]][1])),
                         "OriginalLandingURL": r["OriginalLandingURL"], "Author": r["Author"],
                         "AuthorProfileURL": r["AuthorProfileURL"], "Title": r["Title"], "Rotation": r.get("Rotation", "")})
        print(subset, "scanned; kept so far", len(keep), flush=True)
    keep.sort(key=lambda r: hashlib.md5(r["ImageID"].encode()).hexdigest())
    with open(OUT / "meta.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(keep[0]))
        w.writeheader()
        w.writerows(keep)
    print("META_DONE", len(keep), "CC BY 2.0;", other, "other licences left out", flush=True)


def fetch():
    from PIL import Image

    IMG.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(OUT / "meta.csv", encoding="utf-8")))[:KEEP]
    got = missing = 0
    for i, r in enumerate(rows):
        dest = IMG / f"{r['ImageID']}.jpg"
        if dest.exists():
            got += 1
            continue
        url = MIRROR.format(subset=r["Subset"], img=r["ImageID"])
        for attempt in range(4):
            time.sleep(1.0)
            try:
                data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
                im = Image.open(io.BytesIO(data)).convert("RGB")
                im.thumbnail((640, 640))
                im.save(dest, quality=88)
                got += 1
                break
            except urllib.error.HTTPError as e:
                if e.code in (403, 404):
                    missing += 1
                    break
                time.sleep(10 * (attempt + 1))
            except Exception:  # noqa: BLE001 - a bad file mustn't stop the run
                time.sleep(5)
        if (i + 1) % 200 == 0:
            print(f"{i + 1}/{len(rows)}: {got} saved, {missing} not on the mirror", flush=True)
    print("FETCH_DONE", got, "saved;", missing, "not on the mirror", flush=True)


if __name__ == "__main__":
    {"labels": labels, "meta": meta, "fetch": fetch}[sys.argv[1]]()
