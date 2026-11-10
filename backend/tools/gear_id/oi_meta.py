"""Pick the Open Images photos to fetch and keep their credit lines.

    python -I oi_meta.py <gear_cache dir>

Reads the label extracts (oi_train/val/test/machine.csv: image, source,
label, confidence), chooses
  - gear: any human-verified yes, or a machine label >= 0.8, for a gear class;
  - hard negatives: humans said "no gear" (verified no) and nothing said yes;
  - plain negatives: a sample of validation/test photos with no gear label,
and streams the official image lists (train is 2.5 GB, never saved) keeping
only those rows: author, licence, Flickr page, rotation. Writes oi/meta.csv
and oi/labels.json. Only CC BY 2.0 rows are kept; others are counted.
"""
import csv
import hashlib
import io
import json
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(sys.argv[1])
OUT = ROOT / "oi"
OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "FishEye-gear-data/1.0 (feedback.fisheyefishing@gmail.com)"}
LISTS = {
    "train": "https://storage.googleapis.com/openimages/v6/oidv6-train-images-with-labels-with-rotation.csv",
    "validation": "https://storage.googleapis.com/openimages/2018_04/validation/validation-images-with-rotation.csv",
    "test": "https://storage.googleapis.com/openimages/2018_04/test/test-images-with-rotation.csv",
}
GEAR = {
    "/m/0cqrz": "rod", "/m/0cqsc": "reel", "/m/039j4m": "lure", "/m/039jl6": "spoon",
    "/m/02px2zy": "surface-lure", "/m/0d6dpw": "spinnerbait", "/m/0cqt2": "hook",
    "/m/0g9lh8": "float", "/m/06wbh1": "sinker", "/m/04d__1z": "bait",
    "/m/0h8jqbq": "tackle-box", "/m/02wg8": "tackle", "/m/01f_rk": "fly-fishing",
}
HARD_NEG = 1500
PLAIN_NEG = 1500
CC_BY = "https://creativecommons.org/licenses/by/2.0/"

yes: dict[str, set] = defaultdict(set)
no: dict[str, set] = defaultdict(set)
machine: dict[str, dict] = defaultdict(dict)
for f in ("oi_train.csv", "oi_val.csv", "oi_test.csv", "oi_machine.csv"):
    for img, src, label, conf in csv.reader(open(ROOT / f, encoding="utf-8")):
        if label not in GEAR:
            continue
        c = float(conf)
        if src == "machine":
            machine[img][GEAR[label]] = c
            if c >= 0.8:
                yes[img].add(GEAR[label])
        elif c >= 0.5:
            yes[img].add(GEAR[label])
        else:
            no[img].add(GEAR[label])

gear_ids = set(yes)
hard = sorted((i for i in no if i not in gear_ids), key=lambda i: hashlib.md5(i.encode()).hexdigest())[:HARD_NEG]
wanted = gear_ids | set(hard)
print(f"gear photos {len(gear_ids)}, hard negatives {len(hard)} (of {len([i for i in no if i not in gear_ids])})")


def rows(url):
    # Titles can hold quoted newlines, so the stream goes through csv whole.
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as resp:
        yield from csv.reader(io.TextIOWrapper(resp, encoding="utf-8", newline=""))


kept, other_licence = {}, Counter()
plain_pool = []
for subset, url in LISTS.items():
    it = rows(url)
    header = next(it)
    n = 0
    for row in it:
        n += 1
        if n % 1_000_000 == 0:
            print(f"  {subset}: {n:,} rows read, {len(kept)} kept", flush=True)
        img = row[0]
        sample_plain = subset != "train" and img not in wanted and img not in no
        if img not in wanted and not sample_plain:
            continue
        rec = dict(zip(header, row))
        if rec["License"] != CC_BY:
            other_licence[rec["License"]] += 1
            continue
        if sample_plain:
            plain_pool.append(rec)
        else:
            kept[img] = rec
    print(f"{subset}: {n:,} rows, kept {len(kept)} so far", flush=True)

plain_pool.sort(key=lambda r: hashlib.md5(r["ImageID"].encode()).hexdigest())
for rec in plain_pool[:PLAIN_NEG]:
    kept[rec["ImageID"]] = rec

labels = {}
for img, rec in kept.items():
    if img in gear_ids:
        kind = "gear"
    elif img in no:
        kind = "hard-negative"
    else:
        kind = "negative"
    labels[img] = {"kind": kind, "yes": sorted(yes.get(img, ())), "no": sorted(no.get(img, ())),
                   "machine": machine.get(img, {}), "subset": rec["Subset"]}

cols = ["ImageID", "Subset", "OriginalLandingURL", "License", "Author", "AuthorProfileURL", "Title", "Rotation"]
with open(OUT / "meta.csv", "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for img in sorted(kept):
        w.writerow(kept[img])
(OUT / "labels.json").write_text(json.dumps(labels, indent=0), encoding="utf-8")
kinds = Counter(v["kind"] for v in labels.values())
print("kept:", dict(kinds), "| not CC BY 2.0, skipped:", dict(other_licence))
missing = wanted - set(kept)
print(f"wanted but not in the lists or not CC BY: {len(missing)}")
per = Counter(l for v in labels.values() for l in v["yes"])
print("gear labels:", dict(per.most_common()))
