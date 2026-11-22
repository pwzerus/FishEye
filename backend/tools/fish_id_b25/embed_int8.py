"""Photo vectors from a model folder's int8 encoder on the CPU, in batches, into
the cache fish_id_eval.vectors() reads (named by the recognizer's encoder), so
fish_id_train.py and fish_id_eval.py use them as they are.

    .venv/Scripts/python tools/fish_id_b25/embed_int8.py models/fish-id-b25 fishid_cache            (the test photos; also fishid_cache/commons)
    .venv/Scripts/python tools/fish_id_b25/embed_int8.py models/fish-id-b25 --gate            (the gate's photos)
    .venv/Scripts/python tools/fish_id_b25/embed_int8.py models/fish-id-b25 --oi              (Open Images fish)
    .venv/Scripts/python tools/fish_id_b25/embed_int8.py models/fish-id-b25 --commons-train   (Commons training photos)
    .venv/Scripts/python tools/fish_id_b25/embed_int8.py models/fish-id-b25 --t3              (Commons aquatic animals)
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, ".")
from app.services.fish_id import FishRecognizer  # noqa: E402

model = Path(sys.argv[1])
rec = FishRecognizer(model, use_head=False)
G = Path("F:/tmp/fish_gate")


def run(items: list[tuple[str, Path]], out: Path, batch: int = 8) -> None:
    have = dict(np.load(out)) if out.exists() else {}
    todo = [(k, p) for k, p in items if k not in have]
    print(f"{len(items)} photos, {len(todo)} to embed -> {out}", flush=True)
    t0 = time.time()
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        pix, keys = [], []
        for k, p in chunk:
            try:
                with Image.open(p) as im:
                    pix += [rec._pixels(v) for v in rec.views(im)]
                keys.append(k)
            except Exception as exc:  # noqa: BLE001
                print("  bad", p, exc, flush=True)
        if not keys:
            continue
        with rec._running:
            vecs = rec._session.run(None, {"pixels": np.stack(pix)})[0]
        vecs = vecs.reshape(len(keys), 2, -1).mean(1)
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
        for k, v in zip(keys, vecs):
            have[k] = v.astype(np.float32)
        done = i + len(chunk)
        if done % 800 < batch or done == len(todo):
            np.savez(out, **have)
            print(f"  {done}/{len(todo)}, {(time.time() - t0) / done:.2f} s a photo", flush=True)
    np.savez(out, **have)


name = f"vectors-{rec.encoder.replace('/', '-').replace('@', '-')}-{rec.READING}.npz"
if sys.argv[2] == "--gate":
    neg = json.loads((G / "neg.json").read_text("utf-8"))
    items = [(k, Path(m["path"])) for k, m in neg.items() if Path(m["path"]).exists()]
    for root in ("nonfish", "nonfish_t2", "nonfish_u1", "catch", "catch_flickr"):
        for k in np.load(G / root / "vectors_fish.npz").files:
            hits = [p for p in (G / root).glob(k + ".*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
            if hits:
                items.append((f"{root}|{k}", hits[0]))
    run(items, G / f"gate-{name}")
elif sys.argv[2] == "--commons-train":  # the training set's Commons photos not imported from iNaturalist
    folder = Path("fishid_cache/train")
    photos = [p for p in json.loads((folder / "manifest.json").read_text("utf-8"))["photos"]
              if p.get("source") == "wikimedia-commons" and "inaturalist" not in json.dumps(p).lower()]
    run([(str(p["gbif_id"]), folder / p["file"]) for p in photos if (folder / p["file"]).exists()], G / f"commons_train-{name}")
elif sys.argv[2] == "--t3":  # Commons aquatic animals that aren't fish (collect_nonfish_slow.py)
    imgs = sorted((G / "nonfish_t3").glob("*/*.jpg"))
    run([(f"{p.parent.name}/{p.stem}", p) for p in imgs], G / f"t3-{name}")
elif sys.argv[2] == "--oi":  # Open Images fish (oi_fish.py)
    imgs = sorted((G / "oi_fish/img").glob("*.jpg"))
    run([(p.stem, p) for p in imgs], G / "oi_fish" / name)
else:
    folder = Path(sys.argv[2])
    photos = json.loads((folder / "manifest.json").read_text("utf-8"))["photos"]
    run([(str(p["gbif_id"]), folder / p["file"]) for p in photos if (folder / p["file"]).exists()], folder / name)
print("INT8_DONE", flush=True)
