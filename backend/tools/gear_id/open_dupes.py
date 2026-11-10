"""Leave out new open-catalogue photos that nearly copy a val or test photo.

    python -I open_dupes.py <emb.npz> <labels_all.json> <dupes.json> [threshold]

dupes.py would drop the val photo when a new training photo copies it,
which changes the val set; here the new ("open") photo is the one listed,
so val and test stay exactly the photos the earlier scores were taken on.
PD12M carries Wikimedia Commons files, so some of its photos are the very
Commons photos already in test. Adds to dupes.json (build_labels.py reads it).
"""
import json
import sys
from pathlib import Path

import numpy as np

emb_path, labels_path, dupes_path = sys.argv[1:4]
thr = float(sys.argv[4]) if len(sys.argv) > 4 else 0.95
emb = np.load(emb_path)
labels = json.loads(Path(labels_path).read_text("utf-8"))
ids = [str(i) for i in emb["ids"]]
idx = {k: n for n, k in enumerate(ids)}


def vecs(keys):
    v = emb["vecs"][[idx[k] for k in keys]][:, :2].astype(np.float32).mean(1)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


held = [k for k, v in labels.items() if v["split"] in ("val", "test") and k in idx]
new = [k for k, v in labels.items() if v["source"] == "open" and k in idx]
sim = vecs(new) @ vecs(held).T
hit = sim.max(1) > thr
dropped = sorted(k for k, h in zip(new, hit) if h)
old = json.loads(Path(dupes_path).read_text("utf-8")) if Path(dupes_path).exists() else []
Path(dupes_path).write_text(json.dumps(sorted(set(old) | set(dropped)), indent=0), "utf-8")
print(f"{len(new)} open photos, {len(dropped)} near-copies of val/test photos left out")
for k, h, s, j in zip(new, hit, sim.max(1), sim.argmax(1)):
    if h:
        print(f"  {k}  ~ {held[j]}  {s:.3f}")
