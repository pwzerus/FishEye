"""Near-copies across splits, from one model's vectors.

    python -I dupes.py <emb.npz> <labels.json> <out dupes.json> [threshold]

A train or val photo almost the same as a test photo (cosine of their
vectors above the threshold, 0.95 by default) is listed, so build_labels.py
leaves it out; so is a val photo that copies a train one, and the later of
two near-copies inside test.
"""
import json
import sys
from pathlib import Path

import numpy as np

emb_path, labels_path, out_path = sys.argv[1:4]
thr = float(sys.argv[4]) if len(sys.argv) > 4 else 0.95
emb = np.load(emb_path)
labels = json.loads(Path(labels_path).read_text("utf-8"))
ids = [str(i) for i in emb["ids"]]
keep = [n for n, k in enumerate(ids) if k in labels]
v = emb["vecs"][keep][:, :2].astype(np.float32).mean(1)
v /= np.linalg.norm(v, axis=1, keepdims=True)
ids = [ids[n] for n in keep]
split = np.array([labels[k]["split"] for k in ids])
sim = v @ v.T
np.fill_diagonal(sim, 0)
drop = set()
rank = {"test": 0, "val": 1, "train": 2}
for a, b in zip(*np.nonzero(np.triu(sim > thr))):
    ka, kb = ids[a], ids[b]
    if ka in drop or kb in drop:
        continue
    ra, rb = rank[split[a]], rank[split[b]]
    if ra == rb == 2:
        continue  # two train copies don't skew the test
    drop.add(kb if (rb, kb) > (ra, ka) else ka)
Path(out_path).write_text(json.dumps(sorted(drop), indent=0), encoding="utf-8")
print(f"{len(drop)} near-copies left out (cosine > {thr})")
