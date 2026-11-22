"""BioCLIP 2.5 with nothing fitted on iNaturalist photos, 2026-11-19 (second pass).

Fitted on the training side only, measured on held-out sets:

- Species: BioCLIP 2.5's own text vectors (zero-shot). One number is fitted,
  the logit scale, by log-likelihood on the training set's Wikimedia Commons
  photos (fishid_cache/train, source wikimedia-commons, none imported from
  iNaturalist). The thresholds are the shipped Policy's, unchanged.
- "Is there a fish" gate: a logistic as ft_eval.py fits it. Fish: Open Images
  (CC BY 2.0, oi_fish.py), the training set's Commons photos (weight 3) and the
  Commons and Flickr catch photos it already used (weight 15). Not fish: the
  shipped gate's own photos (Open Images, Commons, Openverse, screenshots),
  less the Open Images ones a person verified as showing a fish. No person
  weighting (the first pass found it changed nothing).
- Measured, never fitted on: the Commons test set (fishid_cache/commons, no
  photographer on both sides), iNaturalist test photos (dev: before March
  2026; clean: from March 2026), the gate's exam.

    .venv/Scripts/python tools/fish_id_b25/fit_gate.py --space int8 [--write] [--explore]   (from backend/)

The vectors are embed_int8.py's (--space gpu reads GPU vectors from an
earlier experiment in F:/tmp/fishdata/b25). The gate's photo sets are those
of tools/fish_gate in its work folder F:/tmp/fish_gate, plus the Open Images
fish (oi_fish.py) and the Commons aquatic animals (queries_t3.json, checked
by eye: has_fish_t3.json). Set OPENBLAS_NUM_THREADS=1 when anything else is
using the CPU.

--write (int8 only) saves models/fish-id-b25/gate.npz in the app's format and
writes the fitted scale into its SOURCE.json (calibrated_logit_scale). --explore prints the gate's
trade-off at other thresholds and the claims accepted on unrelated photos.
"""
import argparse
import csv
import json
import re
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, ".")
from app.cli.fish_id_eval import evaluate, pct  # noqa: E402
from app.services.fish_id import CONFIRMED, POLICY, Candidate, Identification  # noqa: E402
from app.services.fish_id_classes import BY_SLUG, SEA_ONLY  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--space", choices=("gpu", "int8"), required=True)
ap.add_argument("--write", action="store_true")
ap.add_argument("--explore", action="store_true", help="the gate's trade-off and claims accepted on unrelated photos, then stop")
args = ap.parse_args()

D, G, RUN = Path("models/fish-id-b25"), Path("F:/tmp/fish_gate"), Path("F:/tmp/fishdata/b25")
NAME = "vectors-bioclip-2.5-vith14-6e3d04e3d652-int8-middle+whole.npz"
ENCODER = "bioclip-2.5-vith14@6e3d04e3d652/int8"
# BioCLIP 2 with its head and gate, as shipped until 2026-11-21, kept beside the new model to measure against.
SHIPPED = Path("models/fish-id-bioclip2")
SHIPPED_NAME = "vectors-bioclip-2-2957b322090f-int8-middle+whole.npz"
ROOTS = ("nonfish", "nonfish_t2", "nonfish_u1", "catch", "catch_flickr")
CUTOFF = 341_000_000

cls = json.loads((D / "classes.json").read_text("utf-8"))
index = {c["slug"]: i for i, c in enumerate(cls)}
text = np.load(D / "text.npy").astype(np.float32)
fishmask = np.array([c["kind"] != "not_fish" for c in cls])
native = float(json.loads((D / "SOURCE.json").read_text("utf-8"))["logit_scale"])
neg_meta = json.loads((G / "neg.json").read_text("utf-8"))


def from_inat(p):
    return "inaturalist" in json.dumps(p).lower()


TR = Path("fishid_cache/train")
excluded = set(json.loads((TR / "excluded.json").read_text("utf-8")))
train_commons = [p for p in json.loads((TR / "manifest.json").read_text("utf-8"))["photos"]
                 if p.get("source") == "wikimedia-commons" and not from_inat(p) and str(p["gbif_id"]) not in excluded]

# ---- vectors
if args.space == "gpu":
    V = {n: dict(np.load(RUN / f"vec_{n}.npz")) for n in ("test", "commons")}
    gs = {"neg": dict(np.load(RUN / "vec_gate_neg.npz"))} | {r: dict(np.load(RUN / f"vec_gate_{r}.npz")) for r in ROOTS}
    oi = dict(np.load(RUN / "vec_gate_oi.npz"))
    vt = dict(np.load(RUN / "vec_train.npz"))
    ct = {str(p["gbif_id"]): vt[str(p["gbif_id"])] for p in train_commons if str(p["gbif_id"]) in vt}
else:
    V = {"test": dict(np.load(Path("fishid_cache") / NAME)), "commons": dict(np.load(Path("fishid_cache/commons") / NAME))}
    z = dict(np.load(G / f"gate-{NAME}"))
    gs = {"neg": {k: v for k, v in z.items() if k in neg_meta}}
    for r in ROOTS:
        gs[r] = {k.split("|", 1)[1]: v for k, v in z.items() if k.startswith(r + "|")}
    oi = dict(np.load(G / "oi_fish" / NAME))
    ct = dict(np.load(G / f"commons_train-{NAME}"))
train_commons = [p for p in train_commons if str(p["gbif_id"]) in ct]
print(f"space {args.space}: test {len(V['test'])}, Commons test {len(V['commons'])}, Commons training {len(train_commons)}, "
      f"Open Images fish {len(oi)}, " + ", ".join(f"{r} {len(gs[r])}" for r in ("neg", *ROOTS)), flush=True)

# Open Images says a person checked there's a fish in these (labels.csv: every fish id, fetched or not):
# they leave the not-fish photos, and the fetched ones count as fish.
neg_ids = {k.split("oi:", 1)[1] for k in neg_meta if k.startswith("oi-x|oi:")}
fish_ids = {r[0] for r in csv.reader(open(G / "oi_fish/labels.csv", encoding="utf-8"))}
both = sorted(neg_ids & fish_ids)
for k in both:
    gs["neg"].pop(f"oi-x|oi:{k}", None)
# Photos whose credit couldn't be found (b25_credits.py) aren't fitted on.
for k in json.loads((G / "no_credit_b25.json").read_text("utf-8")) if (G / "no_credit_b25.json").exists() else []:
    gs["neg"].pop(k, None)
print(f"shipped not-fish photos that Open Images verified as showing a fish: {len(both)} "
      f"(taken out; {len(set(both) & set(oi))} of them count as fish here)", flush=True)


def groups(d):
    out = {}
    for kk, v in d.items():
        out.setdefault(kk.split("/")[0], []).append(v)
    return {g: np.stack(v).astype(np.float32) for g, v in out.items()}


base = {}
for kk, v in gs["neg"].items():
    base.setdefault(neg_meta[kk]["group"], []).append(v)
base = {g: np.stack(v).astype(np.float32) for g, v in base.items()}
hard, t2, exam = groups(gs["nonfish"]), groups(gs["nonfish_t2"]), groups(gs["nonfish_u1"])
# Aquatic animals that aren't fish, from Commons (collect_nonfish_slow.py, queries_t3.json), checked by eye:
# has_fish_t3.json lists the ones with a fish in them; none may be an exam photo or already a not-fish photo.
t3_file = RUN / "vec_gate_nonfish_t3.npz" if args.space == "gpu" else G / f"t3-{NAME}"
if t3_file.exists():
    has_fish = set(json.loads((Path(__file__).parent / "has_fish_t3.json").read_text("utf-8")))
    seen = {kk.split("/")[-1] for r in ("nonfish", "nonfish_t2", "nonfish_u1") for kk in gs[r]}
    z3 = {kk: v for kk, v in dict(np.load(t3_file)).items() if kk not in has_fish and kk.split("/")[-1] not in seen}
    t2 = {**t2, **groups(z3)}
    print(f"aquatic not-fish photos added: {len(z3)} (left out: {len(has_fish)} with a fish, "
          f"{sum(1 for kk in np.load(t3_file).files if kk.split('/')[-1] in seen)} already used)", flush=True)
CATCH = ['c-bank/162924696', 'c-bank/162924700', 'c-bank/18550330', 'c-bank/35869656', 'c-bank/32732787', 'c-bank/80296753', 'c-hold/157796413', 'c-hold/193809192',
         'c-hold/4992464', 'c-hold/47898691', 'c-hold/45486882', 'c-hold/43821505', 'c-hold/65531731', 'c-hold/65544807', 'c-hold/68988087']
FLICKR = json.loads((G / "catch_flickr.json").read_text("utf-8"))
catch_all = np.stack([gs["catch"][kk] for kk in CATCH] + [gs["catch_flickr"][kk] for kk in FLICKR]).astype(np.float32)
catch_exam = catch_all[1::2]
# Fitted on the Commons catches only: the Flickr ones (and t-flickr below) were
# fetched from Flickr's own servers by a script, which Flickr's terms forbid
# ("robots or similar data gathering"); they are only measured on.
catch_fit = np.stack([gs["catch"][kk] for kk in CATCH][::2]).astype(np.float32)
oi_pos = np.stack(list(oi.values())).astype(np.float32)
ct_x = np.stack([ct[str(p["gbif_id"])] for p in train_commons]).astype(np.float32)
test_pos = np.stack(list(V["test"].values())).astype(np.float32)
ex_all = np.vstack(list(exam.values()))


def obs_id(p):
    m = re.search(r"inaturalist\.org/observations/(\d+)", p["observation"])
    return int(m.group(1)) if m else None


def photos(set_name, keep=lambda p: True, vecs=None):
    folder = {"test": Path("fishid_cache"), "commons": Path("fishid_cache/commons")}[set_name]
    vecs = vecs if vecs is not None else V[set_name]
    ps = [p for p in json.loads((folder / "manifest.json").read_text("utf-8"))["photos"]
          if p["slug"] in BY_SLUG and str(p["gbif_id"]) in vecs and keep(p)]
    return ps, np.stack([vecs[str(p["gbif_id"])] for p in ps]).astype(np.float32)


commons_ps, commons_x = photos("commons", keep=lambda p: not from_inat(p))

# ---- the logit scale, by log-likelihood on the training set's Commons photos
y = np.array([index.get(p["slug"], -1) for p in train_commons])
keep = y >= 0
sims = ct_x[keep] @ text.T
yk = y[keep]
best_nll, scale = None, None
print(f"\nlogit scale by log-likelihood on {int(keep.sum())} Commons training photos (BioCLIP 2.5's own: {native:.1f})")
for s in np.arange(10.0, 150.01, 2.5):
    zz = s * sims
    zz -= zz.max(1, keepdims=True)
    logp = zz - np.log(np.exp(zz).sum(1, keepdims=True))
    nll = float(-logp[np.arange(len(yk)), yk].mean())
    if best_nll is None or nll < best_nll:
        best_nll, scale = nll, float(s)
    if s % 10 == 0:
        print(f"   scale {s:5.1f}: {nll:.3f}", flush=True)
print(f"fitted scale {scale:.1f} (log-likelihood {-best_nll:.3f}); top-1 there {100 * float((sims.argmax(1) == yk).mean()):.1f}%", flush=True)


# ---- gate
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
GW, GBIAS = logistic(xg, yg, np.concatenate([pos_w, neg_w]).astype(np.float32), 1800, .03, 1e-6)


def sig(X, w, b):
    return 1 / (1 + np.exp(-(X @ w + b)))


def share(X, w, b=0.0):
    zz = X @ w.T + b
    zz -= zz.max(1, keepdims=True)
    p = np.exp(zz)
    p /= p.sum(1, keepdims=True)
    return p[:, fishmask].sum(1)


def fish_line(name, gate, fish_share, ex, catch, fish, commons):
    """Does the app think there's a fish: the gate first (>= min_photo), then the fish classes' share (>= min_fish)."""
    def says(X):
        ok = gate(X) >= POLICY.min_photo
        return ok & (fish_share(X) >= POLICY.min_fish) if fish_share else ok
    print(f"{name:34s} unrelated passed {int(says(ex).sum())}/{len(ex)} | catches refused {int((~says(catch)).sum())}/{len(catch)} | "
          f"test fish refused {100 * float((~says(fish)).mean()):.1f}% | Commons test fish refused {100 * float((~says(commons)).mean()):.1f}%", flush=True)


sg = np.load(SHIPPED / "gate.npz")
sh = np.load(SHIPPED / "head.npz")
s_ex = np.vstack(list(groups(dict(np.load(G / "nonfish_u1/vectors_fish.npz"))).values()))
zc, zf = dict(np.load(G / "catch/vectors_fish.npz")), dict(np.load(G / "catch_flickr/vectors_fish.npz"))
s_catch = np.stack([zc[kk] for kk in CATCH] + [zf[kk] for kk in FLICKR]).astype(np.float32)[1::2]
SV = {"test": dict(np.load(Path("fishid_cache") / SHIPPED_NAME)), "commons": dict(np.load(Path("fishid_cache/commons") / SHIPPED_NAME))}
s_test = np.stack(list(SV["test"].values())).astype(np.float32)
s_commons = photos("commons", keep=lambda p: not from_inat(p), vecs=SV["commons"])[1]
s_fishmask = np.array([c["kind"] != "not_fish" for c in json.loads((SHIPPED / "classes.json").read_text("utf-8"))])


def s_share(X):
    zz = X @ sh["w"].T + sh["b"]
    zz -= zz.max(1, keepdims=True)
    p = np.exp(zz)
    p /= p.sum(1, keepdims=True)
    return p[:, s_fishmask].sum(1)


print(f"\nis there a fish? (gate >= {POLICY.min_photo}, then the fish classes' share >= {POLICY.min_fish})")
s_gate = lambda X: sig(X, sg["w"], float(sg["b"]))  # noqa: E731
n_gate = lambda X: sig(X, GW, GBIAS)  # noqa: E731
fish_line("shipped: gate alone", s_gate, None, s_ex, s_catch, s_test, s_commons)
fish_line("shipped: gate, then share", s_gate, s_share, s_ex, s_catch, s_test, s_commons)
fish_line("new: gate alone", n_gate, None, ex_all, catch_exam, test_pos, commons_x)
fish_line("new: gate, then share", n_gate, lambda X: share(X, scale * text), ex_all, catch_exam, test_pos, commons_x)
for g, X in exam.items():
    n = int(((n_gate(X) >= POLICY.min_photo) & (share(X, scale * text) >= POLICY.min_fish)).sum())
    if n:
        print(f"   {g}: {n}/{len(X)} passed", flush=True)


# ---- species, zero-shot, with the gate
class Rec:
    def __init__(self, sc, leave=frozenset()):
        self.W = sc * text
        self.leave = np.array([c["slug"] in leave for c in cls])
        self.name = f"b25-{sc:.0f}"

    def identify_vector(self, v):
        zz = np.where(self.leave, -1e9, self.W @ v)
        p = np.exp(zz - zz.max())
        p /= p.sum()
        order = np.argsort(-p)
        return Identification(tuple(Candidate(cls[i]["slug"], cls[i]["label"], cls[i]["kind"], float(p[i])) for i in order),
                              self.name, float(sig(v, GW, GBIAS)))


s_cls = json.loads((SHIPPED / "classes.json").read_text("utf-8"))


class Shipped:
    name = "shipped"

    def __init__(self, leave=frozenset()):
        self.leave = np.array([c["slug"] in leave for c in s_cls])

    def identify_vector(self, v):
        zz = np.where(self.leave, -1e9, sh["w"] @ v + sh["b"])
        p = np.exp(zz - zz.max())
        p /= p.sum()
        order = np.argsort(-p)
        return Identification(tuple(Candidate(s_cls[i]["slug"], s_cls[i]["label"], s_cls[i]["kind"], float(p[i])) for i in order),
                              self.name, float(sig(v, sg["w"], float(sg["b"]))))


if args.explore:
    from app.services.fish_id import check_claim  # noqa: E402
    from app.cli.fish_id_eval import CLAIMS  # noqa: E402

    print()
    print("the new gate at other thresholds (then the fish share >= 0.5)")
    sh_ex, sh_c, sh_t, sh_m = (share(X, scale * text) >= POLICY.min_fish for X in (ex_all, catch_exam, test_pos, commons_x))
    for t in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
        ok = [(n_gate(X) >= t) & s_ for X, s_ in ((ex_all, sh_ex), (catch_exam, sh_c), (test_pos, sh_t), (commons_x, sh_m))]
        print(f"   gate >= {t:.1f}: unrelated passed {int(ok[0].sum())}/{len(ex_all)} | catches refused {int((~ok[1]).sum())}/{len(catch_exam)} | "
              f"test fish refused {100 * float((~ok[2]).mean()):.1f}% | Commons test fish refused {100 * float((~ok[3]).mean()):.1f}%", flush=True)
    print()
    print("claims accepted on the 431 unrelated photos (every guide fish claimed on each)")
    for name, rec, X, pol in (("shipped", Shipped(), s_ex, POLICY), ("new, shipped Policy", Rec(scale), ex_all, POLICY),
                              ("new, stricter", Rec(scale), ex_all, replace(POLICY, confirm=0.9, group=0.98))):
        acc, photos_hit = 0, 0
        for v in X:
            ident = rec.identify_vector(v)
            a = sum(check_claim(ident, c, pol).accepted for c in CLAIMS)
            acc += a
            photos_hit += a > 0
        print(f"   {name:22s} {acc} claims accepted, on {photos_hit} of {len(X)} photos", flush=True)
    sys.exit(0)


def line(name, rec, set_name, keep=lambda p: True, pol=POLICY, vecs=None):
    ps, X = photos(set_name, keep, vecs)
    r = evaluate(rec, ps, X, pol)["r"]
    t = r["true"]
    print(f"{name:34s} {len(ps):5d} photos | guide top1 {pct(r['top1']['right'], r['top1']['photos'])} | true accepted {pct(t['accepted'], t['claims'])} "
          f"(species {pct(t[CONFIRMED], t['claims'])}, no fish {pct(t['no_fish'], t['claims'])}) | other kind {r['other_group']['accepted']}/{r['other_group']['claims']} | "
          f"same group as species {r['same_group'][CONFIRMED]}/{r['same_group']['claims']} | "
          f"no-guide acc. {r['lookalike_other_group']['accepted']}/{r['lookalike_other_group']['claims']} | no-guide named {pct(r['lookalike']['named'], r['lookalike']['photos'])}", flush=True)


dev = lambda p: (obs_id(p) or 0) < CUTOFF  # noqa: E731
clean = lambda p: (obs_id(p) or 0) >= CUTOFF  # noqa: E731
inland = lambda p: clean(p) and p["slug"] not in SEA_ONLY  # noqa: E731
commons = lambda p: not from_inat(p)  # noqa: E731
strict = replace(POLICY, confirm=0.9, group=0.98)
for title, pol in ((f"shipped Policy (confirm {POLICY.confirm}, group {POLICY.group})", POLICY),
                   (f"stricter, for comparison only (confirm {strict.confirm}, group {strict.group})", strict)):
    print(f"\nBioCLIP 2.5 {args.space}, nothing fitted on iNaturalist: scale {scale:.1f}, {title}")
    line("dev (before March 2026)", Rec(scale), "test", dev, pol)
    line("clean (from March 2026)", Rec(scale), "test", clean, pol)
    line("clean, inland", Rec(scale, SEA_ONLY), "test", inland, pol)
    line("all test photos", Rec(scale), "test", lambda p: True, pol)
    line("Commons test", Rec(scale), "commons", commons, pol)
print("\nshipped (BioCLIP 2 int8, head and gate fitted on iNaturalist photos), same photos")
line("dev (before March 2026)", Shipped(), "test", dev, POLICY, SV["test"])
line("clean (from March 2026)", Shipped(), "test", clean, POLICY, SV["test"])
line("clean, inland", Shipped(SEA_ONLY), "test", inland, POLICY, SV["test"])
line("all test photos", Shipped(), "test", lambda p: True, POLICY, SV["test"])
line("Commons test", Shipped(), "commons", commons, POLICY, SV["commons"])

if args.write:
    assert args.space == "int8", "the app reads int8 vectors"
    np.savez(D / "gate.npz", w=GW, b=np.array(GBIAS, np.float32), encoder=np.array(ENCODER))
    source = json.loads((D / "SOURCE.json").read_text("utf-8"))
    source["calibrated_logit_scale"] = scale
    source["calibrated_on"] = "Wikimedia Commons fish photos in fishid_cache/train not imported from iNaturalist (log-likelihood)"
    (D / "SOURCE.json").write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
    print("written", D / "gate.npz", "and the scale in", D / "SOURCE.json")
print("INAT_FREE_DONE", flush=True)
