"""Photo vectors from an exported ONNX encoder, the way the server will make them.

    python -I embed_onnx.py <image.onnx> <size> <manifest.json> <torch emb.npz> <out.npz> [--reuse out.npz]

Same views as embed.py (middle square, whole photo padded, both mirrored),
mean and std 0.5 (the PE models'); text vectors and classes are copied from
the PyTorch run (the text side isn't shipped, only its vectors).
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

onnx_path, size, manifest, torch_emb, out = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]
MEAN = STD = 0.5
FILL = (127, 127, 127)


def views(img):
    w, h = img.size
    s = size
    scale = s / min(w, h)
    mid = img.resize((max(s, round(w * scale)), max(s, round(h * scale))), Image.Resampling.BICUBIC)
    left, top = (mid.width - s) // 2, (mid.height - s) // 2
    mid = mid.crop((left, top, left + s, top + s))
    scale = s / max(w, h)
    small = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.Resampling.BICUBIC)
    whole = Image.new("RGB", (s, s), FILL)
    whole.paste(small, ((s - small.width) // 2, (s - small.height) // 2))
    return [mid, whole, ImageOps.mirror(mid), ImageOps.mirror(whole)]


def pixels(img):
    return ((np.asarray(img, dtype=np.float32) / 255.0 - MEAN) / STD).transpose(2, 0, 1)


items = json.loads(Path(manifest).read_text("utf-8"))
# --only val,test: just those splits of labels.json; --two-views: no mirrors.
TWO_VIEWS = "--two-views" in sys.argv
if "--only" in sys.argv:
    splits = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    lab = json.loads((Path(manifest).parent / "labels.json").read_text("utf-8"))
    items = [it for it in items if it["id"] in lab and lab[it["id"]]["split"] in splits]
old_ids, old_vecs = [], None
if "--reuse" in sys.argv and Path(sys.argv[sys.argv.index("--reuse") + 1]).exists():
    prev = np.load(sys.argv[sys.argv.index("--reuse") + 1])
    want = {it["id"] for it in items}
    keep = [n for n, i in enumerate(prev["ids"]) if str(i) in want]
    old_ids, old_vecs = [str(prev["ids"][n]) for n in keep], prev["vecs"][keep]
    items = [it for it in items if it["id"] not in set(old_ids)]
    print(f"  reusing {len(old_ids)} photos, {len(items)} to read", flush=True)
opts = ort.SessionOptions()
opts.intra_op_num_threads = 12
opts.log_severity_level = 3
sess = ort.InferenceSession(onnx_path, opts, providers=["CPUExecutionProvider"])
t0 = time.time()
ids, vecs = [], []
for n, it in enumerate(items, 1):
    img = Image.open(it["path"]).convert("RGB")
    if it.get("rotate"):
        img = img.rotate(it["rotate"], expand=True)
    vs = views(img)[:2] if TWO_VIEWS else views(img)
    v = sess.run(None, {"pixels": np.stack([pixels(x) for x in vs])})[0]
    if TWO_VIEWS:
        v = np.concatenate([v, v])  # mirrors left out: checking reads only the first two
    vecs.append(v.astype(np.float16))
    ids.append(it["id"])
    if n % 200 == 0:
        print(f"  {n}/{len(items)} photos, {time.time() - t0:.0f}s", flush=True)
ref = np.load(torch_emb)
parts = ([old_vecs] if old_vecs is not None and len(old_ids) else []) + ([np.stack(vecs)] if vecs else [])
np.savez(out, ids=np.array(old_ids + ids), vecs=np.concatenate(parts), text=ref["text"], classes=ref["classes"], size=size)
print(f"{Path(onnx_path).name}: {len(old_ids) + len(ids)} photos, {time.time() - t0:.0f}s")
