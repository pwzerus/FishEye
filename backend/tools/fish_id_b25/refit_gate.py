"""Refit the "is there a fish" gate on photo vectors read the way the app reads
them, and measure it against the gate installed in models/fish-id
(docs/adr/0067).

The photo sets, their weights and the fit are fit_gate.py's (docs/adr/0066).
The vectors are embed_int8.py's caches for the app's encoder and reading
(FishRecognizer.READING), one photo a run as the app reads it: the int8
encoder quantizes a run as a whole, so a photo read beside others gets a
slightly different vector. Run embed_int8.py first with --gate, --oi,
--commons-train, --t3, fishid_cache and fishid_cache/commons.

    .venv/Scripts/python tools/fish_id_b25/refit_gate.py [--write]      (from backend/)

Both gates are measured at the model's own logit scale (SOURCE.json), through
the app's FishRecognizer: unrelated photos let through, anglers' catches
refused, real fish told "no fish", the species lines and the claims accepted
on unrelated photos. --write replaces models/fish-id/gate.npz (keep the old
one: the server has it until the next deploy). The logit scale stays as it is.
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, ".")
from app.cli.fish_id_eval import CLAIMS, evaluate, pct  # noqa: E402
from app.services.fish_id import CONFIRMED, GROUP, POLICY, FishRecognizer, check_claim  # noqa: E402
from app.services.fish_id_classes import BY_SLUG, SEA_ONLY  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--write", action="store_true", help="replace models/fish-id/gate.npz with the refitted gate")
args = ap.parse_args()

D, G = Path("models/fish-id"), Path("F:/tmp/fish_gate")
rec = FishRecognizer(D)  # with the installed gate
NAME = f"vectors-{rec.encoder.replace('/', '-').replace('@', '-')}-{rec.READING}.npz"
ROOTS = ("nonfish", "nonfish_t2", "nonfish_u1", "catch", "catch_flickr")
CUTOFF = 341_000_000  # iNaturalist observations from March 2026: the clean test photos
CATCH = ["c-bank/162924696", "c-bank/162924700", "c-bank/18550330", "c-bank/35869656", "c-bank/32732787", "c-bank/80296753", "c-hold/157796413",
         "c-hold/193809192", "c-hold/4992464", "c-hold/47898691", "c-hold/45486882", "c-hold/43821505", "c-hold/65531731", "c-hold/65544807",
         "c-hold/68988087"]
FLICKR = json.loads((G / "catch_flickr.json").read_text("utf-8"))
neg_meta = json.loads((G / "neg.json").read_text("utf-8"))


def from_inat(p):
    return "inaturalist" in json.dumps(p).lower()


def obs_id(p):
    m = re.search(r"inaturalist\.org/observations/(\d+)", p.get("observation") or "")
    return int(m.group(1)) if m else 0


def manifest(folder):
    return json.loads((folder / "manifest.json").read_text("utf-8"))["photos"]


def groups(d):
    out = {}
    for kk, v in d.items():
        out.setdefault(kk.split("/")[0], []).append(v)
    return {g: np.stack(v).astype(np.float32) for g, v in out.items()}


# ---- vectors, keyed as embed_int8.py keys them
z = dict(np.load(G / f"gate-{NAME}"))
gs = {"neg": {k: v for k, v in z.items() if k in neg_meta}}
for r in ROOTS:
    gs[r] = {k.split("|", 1)[1]: v for k, v in z.items() if k.startswith(r + "|")}
oi = dict(np.load(G / "oi_fish" / NAME))
t3 = dict(np.load(G / f"t3-{NAME}"))
ct = dict(np.load(G / f"commons_train-{NAME}"))
TR = Path("fishid_cache/train")
excluded = set(json.loads((TR / "excluded.json").read_text("utf-8")))
train_commons = [p for p in manifest(TR) if p.get("source") == "wikimedia-commons" and not from_inat(p)
                 and str(p["gbif_id"]) not in excluded and str(p["gbif_id"]) in ct]

# ---- the photo sets and weights of fit_gate.py
neg_ids = {k.split("oi:", 1)[1] for k in neg_meta if k.startswith("oi-x|oi:")}
fish_ids = {r[0] for r in csv.reader(open(G / "oi_fish/labels.csv", encoding="utf-8"))}
for k in sorted(neg_ids & fish_ids):  # Open Images verified a fish in them
    gs["neg"].pop(f"oi-x|oi:{k}", None)
for k in json.loads((G / "no_credit_b25.json").read_text("utf-8")) if (G / "no_credit_b25.json").exists() else []:
    gs["neg"].pop(k, None)  # no credit found (credits.py)
base = {}
for kk, v in gs["neg"].items():
    base.setdefault(neg_meta[kk]["group"], []).append(v)
base = {g: np.stack(v).astype(np.float32) for g, v in base.items()}
hard, t2 = groups(gs["nonfish"]), groups(gs["nonfish_t2"])
# Commons aquatic animals checked by eye: none with a fish, none an exam photo or already a not-fish photo.
has_fish = set(json.loads((Path(__file__).parent / "has_fish_t3.json").read_text("utf-8")))
seen = {kk.split("/")[-1] for r in ("nonfish", "nonfish_t2", "nonfish_u1") for kk in gs[r]}
t2 = {**t2, **groups({kk: v for kk, v in t3.items() if kk not in has_fish and kk.split("/")[-1] not in seen})}
catch_all = np.stack([gs["catch"][kk] for kk in CATCH] + [gs["catch_flickr"][kk] for kk in FLICKR]).astype(np.float32)
catch_exam = catch_all[1::2]
# Fitted on the Commons catches only; the Flickr ones were fetched from Flickr's servers by a script (fit_gate.py).
catch_fit = np.stack([gs["catch"][kk] for kk in CATCH][::2]).astype(np.float32)
oi_pos = np.stack(list(oi.values())).astype(np.float32)
ct_x = np.stack([ct[str(p["gbif_id"])] for p in train_commons]).astype(np.float32)
exam = np.stack(list(gs["nonfish_u1"].values())).astype(np.float32)


def logistic(xx, yy, ww, steps, lr, l2, sc=25.0):
    Wg, bg = np.zeros(xx.shape[1], np.float32), 0.0
    m1, m2, b1, b2 = np.zeros_like(Wg), np.zeros_like(Wg), 0.0, 0.0
    for t in range(1, steps + 1):
        zz = sc * (xx @ Wg) + bg
        err = (1 / (1 + np.exp(-zz)) - yy) * ww
        g = sc * (xx.T @ err) + l2 * Wg
        gb = float(err.sum())
        m1, m2 = .9 * m1 + .1 * g, .999 * m2 + .001 * g * g
        Wg = Wg - lr * (m1 / (1 - .9 ** t)) / (np.sqrt(m2 / (1 - .999 ** t)) + 1e-8)
        b1, b2 = .9 * b1 + .1 * gb, .999 * b2 + .001 * gb * gb
        bg = bg - lr * (b1 / (1 - .9 ** t)) / (np.sqrt(b2 / (1 - .999 ** t)) + 1e-8)
    return (sc * Wg).astype(np.float32), float(bg)


cf, hf = 5.0, 4.0
allneg = {g: v for g, v in {**base, **hard, **t2}.items() if g != "t-flickr"}
neg_w = np.concatenate([np.full(len(v), hf if (g in hard or g in t2) else 1.0) for g, v in allneg.items()])
neg_w = .5 * neg_w / neg_w.sum()
pos_w = np.concatenate([np.ones(len(oi_pos)), np.full(len(ct_x), 3.0), np.full(len(catch_fit), cf * 3)])
pos_w = .5 * pos_w / pos_w.sum()
xg = np.vstack([oi_pos, ct_x, catch_fit, *allneg.values()]).astype(np.float32)
yg = np.concatenate([np.ones(len(oi_pos) + len(ct_x) + len(catch_fit)), np.zeros(sum(len(v) for v in allneg.values()))]).astype(np.float32)
GW, GB = logistic(xg, yg, np.concatenate([pos_w, neg_w]).astype(np.float32), 1800, .03, 1e-6)
print(f"{rec.encoder}, read as {rec.READING}: fitted on {len(oi_pos)} Open Images fish, {len(ct_x)} Commons fish, "
      f"{len(catch_fit)} catches; {int((yg == 0).sum())} not fish", flush=True)

# ---- measured through the app's recognizer, with each gate
V = {"test": dict(np.load(Path("fishid_cache") / NAME)), "commons": dict(np.load(Path("fishid_cache/commons") / NAME))}
clean_ps = [p for p in manifest(Path("fishid_cache")) if p["slug"] in BY_SLUG and obs_id(p) >= CUTOFF and str(p["gbif_id"]) in V["test"]]
commons_ps = [p for p in manifest(Path("fishid_cache/commons")) if p["slug"] in BY_SLUG and not from_inat(p) and str(p["gbif_id"]) in V["commons"]]
c_X = np.stack([V["test"][str(p["gbif_id"])] for p in clean_ps]).astype(np.float32)
m_X = np.stack([V["commons"][str(p["gbif_id"])] for p in commons_ps]).astype(np.float32)
inland = [i for i, p in enumerate(clean_ps) if p["slug"] not in SEA_ONLY]


class Inland:
    """The reading for a catch far from the sea (Identification.inland)."""

    def identify_vector(self, v):
        return rec.identify_vector(v).inland()


def says_fish(X):
    return np.array([rec.identify_vector(v).fish_probability >= POLICY.min_fish for v in X])


installed = rec._gate
for title, gate in (("installed gate", installed), ("refitted gate", (GW, GB))):
    rec._gate = gate
    print(f"\n== {title}{' (none)' if gate is None else ''}, logit scale as installed")
    print(f"   is there a fish: unrelated passed {int(says_fish(exam).sum())}/{len(exam)} | anglers' catches refused "
          f"{int((~says_fish(catch_exam)).sum())}/{len(catch_exam)} (all {int((~says_fish(catch_all)).sum())}/{len(catch_all)}) | "
          f"clean fish refused {100 * float((~says_fish(c_X)).mean()):.1f}% | Commons fish refused {100 * float((~says_fish(m_X)).mean()):.1f}%",
          flush=True)
    for name, r, ps, X in (("clean (from March 2026)", rec, clean_ps, c_X), ("clean, inland", Inland(), [clean_ps[i] for i in inland], c_X[inland]),
                           ("Commons test", rec, commons_ps, m_X)):
        res = evaluate(r, ps, X, POLICY)["r"]
        t, s = res["true"], res["same_group"]
        print(f"   {name:24s} {len(ps):5d} | top-1 {pct(res['top1']['right'], res['top1']['photos'])} | honest accepted "
              f"{pct(t['accepted'], t['claims'])} (species {pct(t[CONFIRMED], t['claims'])}, group {pct(t[GROUP], t['claims'])}) | "
              f"other kind {res['other_group']['accepted']}/{res['other_group']['claims']} | look-alike as the species "
              f"{s[CONFIRMED]}/{s['claims']} | no-guide accepted {res['lookalike_other_group']['accepted']}", flush=True)
    hit = [sum(check_claim(rec.identify_vector(v), c, POLICY).accepted for c in CLAIMS) for v in exam]
    print(f"   claims accepted on the {len(exam)} unrelated photos: {sum(hit)}, on {sum(h > 0 for h in hit)} photos", flush=True)
rec._gate = installed

if args.write:
    np.savez(D / "gate.npz", w=GW, b=np.array(GB, np.float32), encoder=np.array(rec.encoder), reading=np.array(rec.READING))
    print("\nwritten", D / "gate.npz")
print("REFIT_DONE", flush=True)
