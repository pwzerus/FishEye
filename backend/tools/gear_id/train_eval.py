"""Zero-shot and trained scores for one model's vectors.

    python -I train_eval.py <emb.npz> <labels.json> <out.json> [--save-head head.npz]

labels.json: {id: {"allowed": [classes], "split": "train"|"val"|"test",
                   "source": "oi"|"commons"|"pick", "checked": bool}}
"checked" photos were labelled by eye with the exact item; only those count
for the fine score.

Open Images says "a lure", not which lure, so what is learnt from photos is
the group (rod, reel, lure kinds, hook, bait, ... or not gear), and which
item inside the group is left to the text vectors, the model's own
knowledge (taxonomy.GROUPS):
    P(item) = sum over its groups g of P(g | photo) * P(item | g, photo)
P(g | photo) is a linear layer started from the mean text vector of g's
items (the not-gear group from the x-* prompts) and kept near it; P(item |
g) is a softmax of text similarity over g's items. A flat head over all
items, trained the same way, is scored too: it collapses the items inside a
group onto one, which is why the split. Settings are chosen on val; test is
scored once.
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent))
from taxonomy import GROUPS, group_of  # noqa: E402

emb_path, labels_path, out_path = sys.argv[1:4]
save_head = sys.argv[sys.argv.index("--save-head") + 1] if "--save-head" in sys.argv else None
emb = dict(np.load(emb_path))
if "--text" in sys.argv:  # other prompts' text vectors (embed.py with manifest "-")
    other = np.load(sys.argv[sys.argv.index("--text") + 1])
    emb["text"], emb["classes"] = other["text"], other["classes"]
labels = json.loads(Path(labels_path).read_text("utf-8"))
all_classes = [str(c) for c in emb["classes"]]
keep_cls = [i for i, c in enumerate(all_classes) if not c.startswith("f-")]  # f-*: data cleaning only
classes = [all_classes[i] for i in keep_cls]
C = len(classes)
idx = {c: i for i, c in enumerate(classes)}
is_gear = np.array([not c.startswith("x-") for c in classes])
text = torch.tensor(emb["text"][keep_cls], dtype=torch.float32)

# Groups: GROUPS plus not-gear (all x-* classes).
gnames = list(GROUPS) + ["not-gear"]
members = [[idx[c] for c in GROUPS[g]] for g in GROUPS] + [[i for i, c in enumerate(classes) if c.startswith("x-")]]
G = len(gnames)
M = torch.zeros(G, C)  # membership
for g, mem in enumerate(members):
    M[g, mem] = 1
gtext = torch.stack([text[mem].mean(0) for mem in members])
gtext = gtext / gtext.norm(dim=-1, keepdim=True)

rows = [(i, str(k)) for i, k in enumerate(emb["ids"]) if str(k) in labels]
vec4 = torch.tensor(emb["vecs"][[i for i, _ in rows]].astype(np.float32))  # (N, 4, D)
keys = [k for _, k in rows]
mean = vec4[:, :2].mean(1)
mean = mean / mean.norm(dim=-1, keepdim=True)  # how a photo is read when it is checked
allowed = torch.zeros(len(keys), C, dtype=torch.bool)
for n, k in enumerate(keys):
    for c in labels[k]["allowed"]:
        allowed[n, idx[c]] = True
g_allowed = (allowed.float() @ M.T) > 0  # (N, G)
split = np.array([labels[k]["split"] for k in keys])
checked = np.array([bool(labels[k].get("checked")) for k in keys])
gear_photo = allowed[:, torch.tensor(is_gear)].any(1).numpy()


def scores(p, sel):
    """Scores from item probabilities p (N, C) on the photos in sel."""
    p = p.numpy() if torch.is_tensor(p) else p
    a = allowed.numpy()
    out = {}
    g = sel & gear_photo
    pg = np.where(is_gear, p, 0)  # "if it is gear, which?"
    top = np.argsort(-pg, 1)
    right1 = a[np.arange(len(a)), top[:, 0]]
    right3 = np.array([a[n, top[n, :3]].any() for n in range(len(a))])
    groups_ok = np.array([bool(group_of(classes[top[n, 0]]) & set().union(*(group_of(classes[j]) for j in np.flatnonzero(a[n]))))
                          for n in range(len(a))])
    p_gear = p[:, is_gear].sum(1)
    neg = sel & ~gear_photo
    out["is_gear_found"] = float((p_gear[g] >= 0.5).mean()) if g.any() else None
    out["not_gear_rejected"] = float((p_gear[neg] < 0.5).mean()) if neg.any() else None
    out["group_acc"] = float(groups_ok[g].mean()) if g.any() else None
    out["allowed_acc"] = float(right1[g].mean()) if g.any() else None
    f = g & checked
    out["fine_acc"] = float(right1[f].mean()) if f.any() else None
    out["fine_top3"] = float(right3[f].mean()) if f.any() else None
    out["n_gear"], out["n_not_gear"], out["n_checked"] = int(g.sum()), int(neg.sum()), int(f.sum())
    return out


def within(x, scale):
    """P(item | group, photo) for every group, as (N, G, C)."""
    s = scale * x @ text.T  # (N, C)
    s = s.unsqueeze(1).expand(-1, G, -1).masked_fill(M.unsqueeze(0) == 0, -1e9)
    return torch.softmax(s, -1)


def zero_shot(scale=100.0):
    return torch.softmax(scale * mean @ text.T, -1)


N_GEAR = int(is_gear.sum())


def weights(tr):
    """Rarer labels count more (1/sqrt of how many share it); "some gear"
    photos (Open Images' Tackle) teach only gear-or-not, at a third."""
    key = [tuple(sorted(labels[k]["allowed"])) for k, t in zip(keys, tr.tolist()) if t]
    count = Counter(key)
    w = torch.tensor([(0.3 if len(k) == N_GEAR else 1.0) / count[k] ** 0.5 for k in key]).repeat_interleave(4)
    return w / w.mean()


def fit(W0, al_full, lam, scale, epochs, lr=2e-3):
    """A linear layer from W0, loss -log P(one of the allowed rows)."""
    tr = torch.tensor(split == "train")
    x = vec4[tr].reshape(-1, vec4.shape[-1])  # every view is a sample
    al = al_full[tr].repeat_interleave(4, 0)
    w = weights(tr)
    W = W0.clone().requires_grad_(True)
    b = torch.zeros(len(W0), requires_grad=True)
    opt = torch.optim.Adam([W, b], lr=lr)
    for _ in range(epochs):
        opt.zero_grad()
        logp = torch.log_softmax(scale * x @ W.T + b, -1)
        nll = -(torch.logsumexp(logp.masked_fill(~al, -1e9), -1))
        loss = (w * nll).mean() + lam * ((W - W0) ** 2).sum()
        loss.backward()
        opt.step()
    return W.detach(), b.detach()


def zs_groups(scale=100.0):
    """Zero-shot P(group): the items' zero-shot probabilities summed per group."""
    pg = zero_shot(scale) @ M.T
    return pg / pg.sum(-1, keepdim=True)


def hier(Wg, bg, scale, alpha=1.0, fine_scale=100.0):
    """P(item); the group part mixes the fitted head (alpha) with zero-shot."""
    pg = alpha * torch.softmax(scale * mean @ Wg.T + bg, -1) + (1 - alpha) * zs_groups(fine_scale)
    return (pg.unsqueeze(-1) * within(mean, fine_scale)).sum(1)  # (N, C)


def flat(W, b, scale):
    return torch.softmax(scale * mean @ W.T + b, -1)


def pick(s):
    """One number to choose settings by, on val: the fine score on the photos
    checked by eye, the group score, and finding gear and not-gear."""
    vals = [s[k] for k in ("fine_acc", "group_acc", "is_gear_found", "not_gear_rejected") if s[k] is not None]
    return sum(vals) / len(vals)


def search(make, W0, al, label):
    trials = []
    for lam in (0.01, 0.1, 1.0):
        for scale in (30.0, 60.0):
            for epochs in (150, 400):
                W, b = fit(W0, al, lam, scale, epochs)
                trials.append((pick(scores(make(W, b, scale), val)), lam, scale, epochs))
    _, lam, scale, epochs = max(trials)
    W, b = fit(W0, al, lam, scale, epochs)
    print(f"  {label}: lam {lam} scale {scale} epochs {epochs}", flush=True)
    return W, b, {"lam": lam, "scale": scale, "epochs": epochs}


val, test = split == "val", split == "test"
result = {"model": Path(emb_path).stem, "classes": C, "groups": G,
          "train_photos": int((split == "train").sum()), "val_photos": int(val.sum())}
best_zs = max((100.0, 30.0, 300.0), key=lambda s: pick(scores(zero_shot(s), val)))
zs = zero_shot(best_zs)
result["zero_shot"] = {"scale": best_zs, "val": scores(zs, val), "test": scores(zs, test)}

Wf, bf, cfg_f = search(lambda W, b, s: flat(W, b, s), text, allowed, "flat head")
result["flat_head"] = {**cfg_f, "val": scores(flat(Wf, bf, cfg_f["scale"]), val),
                       "test": scores(flat(Wf, bf, cfg_f["scale"]), test)}
Wg, bg, cfg_g = search(lambda W, b, s: hier(W, b, s), gtext, g_allowed, "group head")
# How much of the group part to take from the head, the rest from zero-shot.
alpha = max((0.25, 0.5, 0.75, 1.0), key=lambda a: pick(scores(hier(Wg, bg, cfg_g["scale"], a), val)))
cfg_g["alpha"] = alpha
print(f"  mix: alpha {alpha}", flush=True)
ph = hier(Wg, bg, cfg_g["scale"], alpha)
result["group_head"] = {**cfg_g, "val": scores(ph, val), "test": scores(ph, test)}
result["test_by_source"] = {}
for src in sorted({labels[k].get("source", "?") for k in keys}):
    m = test & np.array([labels[k].get("source") == src for k in keys])
    if m.any():
        result["test_by_source"][src] = {"zero_shot": scores(zs, m), "group_head": scores(ph, m)}
Path(out_path).write_text(json.dumps(result, indent=1), encoding="utf-8")
if save_head:
    np.savez(save_head, wg=(cfg_g["scale"] * Wg).numpy().astype(np.float32), bg=bg.numpy().astype(np.float32),
             alpha=np.float32(alpha), fine_scale=np.float32(100.0),
             groups=np.array(gnames), members=M.numpy().astype(np.uint8), text=text.numpy().astype(np.float32),
             classes=np.array(classes))
fmt = lambda v: "  -  " if v is None else f"{v:5.1%}"  # noqa: E731
t = {k: result[k]["test"] for k in ("zero_shot", "flat_head", "group_head")}
print(f"{result['model']}: TEST zero-shot | flat head | group head  "
      f"(gear {t['zero_shot']['n_gear']}, not gear {t['zero_shot']['n_not_gear']}, checked {t['zero_shot']['n_checked']})")
for k in ("is_gear_found", "not_gear_rejected", "group_acc", "allowed_acc", "fine_acc", "fine_top3"):
    print(f"  {k:18s} {fmt(t['zero_shot'][k])} | {fmt(t['flat_head'][k])} | {fmt(t['group_head'][k])}")
