"""Training photos that would teach the wrong thing, from two models' vectors.

    python -I clean_train.py <labels.json> <out unfit.json> <emb.npz> [<emb.npz> ...]

Test photos are checked by eye and never listed. Of the rest, left out are:
  - drawings, engravings, comics, paintings, diagrams and museum pieces:
    P("a photo") among the f-* prompts, averaged over the models, below 0.4.
    On the 101 hand-checked Commons photos (SigLIP2-SO400M and PE-Core-L
    averaged) that catches 25 of 30 such pictures and loses 7 of 71 photos;
    either model alone did worse (21/30 and 6 lost; 28/30 and 13 lost);
  - gear-labelled photos whose likeliest class of all is a fish (same
    average): a catch shot with a rod in it would teach "fish photo -> rod".
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

labels_path, out_path, *emb_paths = sys.argv[1:]
labels = json.loads(Path(labels_path).read_text("utf-8"))
P_PHOTO = 0.4
photo_p: dict[str, list] = {}
main_p: dict[str, list] = {}
for path in emb_paths:
    emb = np.load(path)
    classes = [str(c) for c in emb["classes"]]
    text = emb["text"]
    f_idx = [i for i, c in enumerate(classes) if c.startswith("f-")]
    photo = f_idx.index(classes.index("f-photo"))
    main_idx = [i for i, c in enumerate(classes) if not c.startswith("f-")]
    main_names = [classes[i] for i in main_idx]
    for n, key in enumerate(str(k) for k in emb["ids"]):
        lab = labels.get(key)
        if lab is None or lab["split"] == "test":
            continue
        v = emb["vecs"][n, :2].astype(np.float32).mean(0)
        v /= np.linalg.norm(v)
        s = 100 * text @ v
        f = np.exp(s[f_idx] - s[f_idx].max())
        photo_p.setdefault(key, []).append(f[photo] / f.sum())
        m = np.exp(s[main_idx] - s[main_idx].max())
        main_p.setdefault(key, []).append(m / m.sum())
unfit, why = [], Counter()
fish = main_names.index("x-fish")
for key, ps in photo_p.items():
    lab = labels[key]
    gear = not lab["allowed"][0].startswith("x-")
    if np.mean(ps) < P_PHOTO:
        unfit.append(key)
        why[f"not a photo ({lab['source']})"] += 1
    elif gear and int(np.argmax(np.mean(main_p[key], 0))) == fish:
        unfit.append(key)
        why[f"a fish photo labelled gear ({lab['source']})"] += 1
Path(out_path).write_text(json.dumps(sorted(unfit), indent=0), encoding="utf-8")
print(f"{len(unfit)} training photos left out:", dict(why))
