"""Who took the photos models/fish-id-b25/gate.npz was fitted on (fit_gate.py):
-> models/fish-id-b25/GATE_CREDITS.json. BioCLIP 2.5 ships with no classifier
head, so this is the only photo credits file; its logit scale was fitted on
the Commons training photos, credited here too.

    .venv/Scripts/python tools/fish_id_b25/credits.py   (from backend/, before fit_gate.py: it leaves out what has no credit)
"""
import ast
import csv
import glob
import html
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
B = Path("F:/FishEye/backend")
G = Path("F:/tmp/fish_gate")
GC = B / "gear_cache"
NAME = "vectors-bioclip-2.5-vith14-6e3d04e3d652-int8-middle+whole.npz"
CATCH = ['c-bank/162924696', 'c-bank/162924700', 'c-bank/18550330', 'c-bank/35869656', 'c-bank/32732787', 'c-bank/80296753', 'c-hold/157796413', 'c-hold/193809192',
         'c-hold/4992464', 'c-hold/47898691', 'c-hold/45486882', 'c-hold/43821505', 'c-hold/65531731', 'c-hold/65544807', 'c-hold/68988087']


def plain(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s or "")).strip()


fish, not_fish, missing, uncredited = [], [], Counter(), []

# ---- fish
for r in csv.DictReader(open(G / "oi_fish/meta.csv", encoding="utf-8")):
    if (G / "oi_fish/img" / f"{r['ImageID']}.jpg").exists():
        fish.append(dict(creator=r["Author"], licence="CC BY 2.0", url=r["OriginalLandingURL"]))
used = set(np.load(G / f"commons_train-{NAME}").files)
excluded = set(json.loads((B / "fishid_cache/train/excluded.json").read_text("utf-8")))
for p in json.loads((B / "fishid_cache/train/manifest.json").read_text("utf-8"))["photos"]:
    if str(p["gbif_id"]) in used and str(p["gbif_id"]) not in excluded:
        fish.append(dict(creator=p.get("creator") or "", licence=p.get("licence"), url=p.get("observation")))
for key in CATCH[::2]:
    group, pid = key.split("/")
    found = {str(f["pageid"]): f for f in json.loads((G / "catch" / group / "found.json").read_text("utf-8")).values()}
    f = found[pid]
    fish.append(dict(creator=plain(f.get("artist_html")), licence=f.get("licence"), url=f.get("page_url")))

# ---- not fish: the shipped gate's own, less those Open Images verified as showing a fish
meta = json.loads((G / "neg.json").read_text("utf-8"))
fish_ids = {r[0] for r in csv.reader(open(G / "oi_fish/labels.csv", encoding="utf-8"))}
oi = {r["ImageID"]: r for r in csv.DictReader(open(GC / "oi/meta.csv", encoding="utf-8"))}
opened = {}
for f in glob.glob(str(GC / "open2/candidates-*.json")):
    d = json.load(open(f, encoding="utf-8"))
    for L in (d.values() if isinstance(d, dict) else [d]):
        for c in (L if isinstance(L, list) else [L]):
            if isinstance(c, dict) and "id" in c:
                opened[c["id"]] = c
files = json.load(open(GC / "commons_cat/files.json", encoding="utf-8"))
by_id = {str(v.get("pageid")): v for v in (files.values() if isinstance(files, dict) else files) if isinstance(v, dict)}
# The gear page's photos as they stood when those were copied (before 8201bfe self-hosted them).
src = subprocess.run(["git", "-C", "F:/FishEye", "show", "dd12d7e:backend/app/knowledge/gear_photos.py"],
                     capture_output=True, check=True).stdout.decode("utf-8")
picked = {}
for node in ast.parse(src).body:
    if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "PHOTOS":
        for k, call in zip(node.value.keys, node.value.values):
            picked[k.value] = {kw.arg: ast.literal_eval(kw.value) for kw in call.keywords}


def same_shape(path, p):
    w, h = Image.open(path).size
    return abs(w / h - p["width"] / p["height"]) < 0.03


for key, v in meta.items():
    if v["group"] in ("screens", "real-screens"):
        continue
    k = key.split("|", 1)[1]
    if k.startswith("oi:") and k[3:] in fish_ids:
        continue
    if k.startswith("oi:") and k[3:] in oi:
        r = oi[k[3:]]
        not_fish.append(dict(creator=r["Author"], licence=r["License"], url=r["OriginalLandingURL"]))
    elif k in opened:
        c = opened[k]
        not_fish.append(dict(creator=c.get("author"), licence=c.get("licence"), url=c.get("page")))
    elif by_id.get(k.split(":")[-1]):
        c = by_id[k.split(":")[-1]]
        not_fish.append(dict(creator=plain(c.get("creator") or c.get("artist") or c.get("artist_html")), licence=c.get("licence"), url=c.get("page_url")))
    elif k.startswith("pick:") and k[5:] in picked and same_shape(v["path"], picked[k[5:]]):
        p = picked[k[5:]]
        not_fish.append(dict(creator=p["author"], licence=p["licence"], url=p["page"]))
    else:
        missing[k.split(":")[0]] += 1
        uncredited.append(key)

# Commons photos found for the gates (t-flickr, fetched from Flickr's servers, is not fitted on)
has_fish = set(json.loads((Path(__file__).parent / "has_fish_t3.json").read_text("utf-8")))
seen = set()
for root in ("nonfish", "nonfish_t2", "nonfish_t3"):
    for fj in sorted(glob.glob(str(G / root / "*" / "found.json"))):
        group = Path(fj).parent.name
        if group == "t-flickr":
            continue
        for f in json.load(open(fj, encoding="utf-8")).values():
            key = f"{group}/{f['pageid']}"
            if not (Path(fj).parent / f"{f['pageid']}.jpg").exists() or key in has_fish:
                continue
            if root == "nonfish_t3" and str(f["pageid"]) in seen:
                continue
            seen.add(str(f["pageid"]))
            not_fish.append(dict(creator=plain(f.get("artist_html")), licence=f.get("licence"), url=f.get("page_url")))

out = B / "models/fish-id-b25/GATE_CREDITS.json"
out.write_text(json.dumps(dict(
    note=("Photos models/fish-id/gate.npz (BioCLIP 2.5) was fitted on, and the Wikimedia Commons fish photos its "
          "logit scale was fitted on. No iNaturalist photo was used. With thanks to their creators. No photo ships; "
          "only the fitted weights do. Also fitted on screenshots of FishEye and on synthetic screens and documents "
          "made by tools/fish_gate/make_screens.py."),
    fish=fish,
    not_fish=not_fish,
), ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
# A photo whose credit can't be found is left out of the fit (b25_inat_free.py reads this).
(G / "no_credit_b25.json").write_text(json.dumps(sorted(uncredited)), encoding="utf-8")
print(f"fish {len(fish)}, not fish {len(not_fish)}; no record, left out of the fit: {dict(missing)}")
print(Counter((x.get("licence") or "")[:30] for x in fish + not_fish).most_common(10))
