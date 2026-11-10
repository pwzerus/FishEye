"""labels.json for train_eval.py, and the manifest for embed.py.

    python -I build_labels.py <gear_cache dir>

Sources, each photo's split decided by its author (a photographer's series
stays on one side, so near-copies can't be learnt and then tested):
  oi       Open Images, labels from oi/labels.json (taxonomy.OI_ALLOWS)
  commons  Commons category photos (commons_cat/files.json, COMMONS_ALLOWS)
  pick     the 46 photos picked by eye for the gear page (test only)
  open     photos found in open catalogues by their text (open2/), only
           those labelled by eye, all in train
handcheck.json, labels given by eye ({id: {"allowed": [...]}} or
{id: {"drop": true}}), overrides any source label and marks the photo
"checked". Ids in dupes.json (near-copies across splits) are left out, and
so are training photos in unfit.json (clean_train.py).
Author buckets: 0-1 test, 2 val, 3-9 train.
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from taxonomy import COMMONS_ALLOWS, NOT_GEAR, OI_ALLOWS  # noqa: E402

ROOT = Path(sys.argv[1])
WORK = ROOT / "work"
WORK.mkdir(exist_ok=True)


def split_of(author: str) -> str:
    b = int(hashlib.md5(author.strip().lower().encode()).hexdigest(), 16) % 10
    return "test" if b < 2 else "val" if b == 2 else "train"


hand = json.loads((Path(__file__).parent / "handcheck.json").read_text("utf-8")) if (Path(__file__).parent / "handcheck.json").exists() else {}
dupes = set(json.loads((WORK / "dupes.json").read_text("utf-8"))) if (WORK / "dupes.json").exists() else set()
# Not photos, or catch shots labelled gear (clean_train.py); never test photos.
unfit = set(json.loads((WORK / "unfit.json").read_text("utf-8"))) if (WORK / "unfit.json").exists() else set()
labels, labels_all, manifest = {}, {}, []


def add(key, path, allowed, split, source, rotate=0):
    if not path.exists():
        return
    # Every photo gets vectors (the cleaning and checking steps read them);
    # only the ones kept get a label.
    manifest.append({"id": key, "path": str(path), "rotate": rotate})
    h = hand.get(key)
    if h and h.get("drop"):
        return
    rec = {"allowed": sorted(set(h["allowed"] if h else allowed)), "split": split, "source": source, "checked": bool(h)}
    labels_all[key] = rec  # what clean_train.py and dupes.py read, so their lists don't shrink run to run
    if key in dupes or (key in unfit and split != "test"):
        return
    labels[key] = rec


# Which Open Images labels to believe, checked by eye on the test photos
# (work/notes-oi.txt, 2026-11-07): "crowdsource-verification" yeses (the
# Crowdsource app) were wrong 35 times in 35 for Fishing rod (horses, buses,
# a conference); the raters' "verification" and machine labels >= 0.8 were
# right. And /m/02wg8 "Tackle" is the sports tackle (40 in 40 were football
# or rugby), so those photos are not gear.
MID = {"/m/0cqrz": "rod", "/m/0cqsc": "reel", "/m/039j4m": "lure", "/m/039jl6": "spoon", "/m/02px2zy": "surface-lure",
       "/m/0d6dpw": "spinnerbait", "/m/0cqt2": "hook", "/m/0g9lh8": "float", "/m/06wbh1": "sinker",
       "/m/04d__1z": "bait", "/m/0h8jqbq": "tackle-box", "/m/01f_rk": "fly-fishing"}
trusted: dict[str, set] = {}
crowd: set[str] = set()
for f in ("oi_train.csv", "oi_val.csv", "oi_test.csv", "oi_machine.csv"):
    for img, src, mid, conf in csv.reader(open(ROOT / f, encoding="utf-8")):
        if mid not in MID:
            continue
        c = float(conf)
        if src == "crowdsource-verification":
            if c >= 0.5:
                crowd.add(img)
        elif (src == "machine" and c >= 0.8) or (src == "verification" and c >= 0.5):
            trusted.setdefault(img, set()).add(MID[mid])

oi_labels = json.loads((ROOT / "oi" / "labels.json").read_text("utf-8"))
for rec in csv.DictReader(open(ROOT / "oi" / "meta.csv", encoding="utf-8")):
    img = rec["ImageID"]
    lab = oi_labels[img]
    if img in trusted:
        allowed = sorted({c for y in trusted[img] for c in OI_ALLOWS[y]})
    elif lab["kind"] == "gear" and img in crowd and f"oi:{img}" not in hand:
        continue  # only the Crowdsource app says gear: unknown
    else:
        allowed = NOT_GEAR  # no gear label, a verified "no", or the sports tackle
    rot = int(float(rec["Rotation"] or 0))
    add(f"oi:{img}", ROOT / "oi" / "img" / f"{img}.jpg", allowed, split_of(rec["AuthorProfileURL"] or rec["Author"]),
        "oi", rotate=rot)

picked = {line.split("\t")[1].strip() for line in (ROOT / "picks.tsv").read_text("utf-8").splitlines()
          if line.strip() and not line.startswith("#")}
# Commons categories that aren't angling gear a shopper meets: museum stone
# weights, glass net floats, commercial longlines, knot diagrams, shacks, art.
NOT_ANGLING = ("Māori", "Bara (", "Longlines", "Fishing balls", "Fishing knots", "Ice fishing shacks", "Solidor")
cfiles = ROOT / "commons_cat" / "files.json"
if cfiles.exists():
    for key, f in json.loads(cfiles.read_text("utf-8")).items():
        if f["title"] in picked or f["category"].startswith(NOT_ANGLING):
            continue  # the picks are a test set of their own
        add(f"commons:{key}", ROOT / "commons_cat" / "img" / f"{key}.jpg", COMMONS_ALLOWS[f["kind"]],
            split_of(f.get("creator") or f["title"]), "commons")

# Photos found by their text in open catalogues (scan_catalogs.py,
# fetch_candidates.py, 2026-11-07): only the ones labelled by eye count, and
# all of them train, so val and test stay the photos the earlier scores were
# taken on and a new score can be compared with the old.
for cands in sorted((ROOT / "open2").glob("candidates-*.json")):
    for c in json.loads(cands.read_text("utf-8")):
        if c["id"] in hand:
            add(c["id"], Path(c["path"]), [], "train", "open")

for line in (ROOT / "picks.tsv").read_text("utf-8").splitlines():
    if not line.strip() or line.startswith("#"):
        continue
    item = line.split("\t")[0].strip()
    key = f"pick:{item}"
    labels_before = len(labels)
    add(key, ROOT / "test330" / f"{item}.jpg", [item], "test", "pick")
    if key in labels_all:
        labels_all[key]["checked"] = True  # picked by eye as a clear photo of the item (labels shares the record)

(WORK / "labels.json").write_text(json.dumps(labels, indent=0), encoding="utf-8")
(WORK / "labels_all.json").write_text(json.dumps(labels_all, indent=0), encoding="utf-8")
(WORK / "manifest.json").write_text(json.dumps(manifest, indent=0), encoding="utf-8")
from collections import Counter  # noqa: E402

print("photos:", len(labels))
print("by source and split:", dict(Counter((v["source"], v["split"]) for v in labels.values())))
print("checked by eye:", sum(v["checked"] for v in labels.values()))
