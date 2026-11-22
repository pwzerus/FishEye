"""Photo vectors from a model folder's int8 encoder on the CPU, read as the app
reads them (FishRecognizer.embed, one photo a run), into the cache
fish_id_eval.vectors() reads (named by the recognizer's encoder and reading),
so fish_id_eval.py and refit_gate.py use them as they are (fit_gate.py reads
the "middle+whole" caches it was fitted on, docs/adr/0066).

One photo a run because the int8 encoder quantizes a run as a whole: read 8 to
a run, as the "middle+whole" caches were until 2026-11-22, a photo gets a
slightly different vector than in the app (docs/adr/0067).

    .venv/Scripts/python tools/fish_id_b25/embed_int8.py models/fish-id fishid_cache            (the test photos; also fishid_cache/commons)
    .venv/Scripts/python tools/fish_id_b25/embed_int8.py models/fish-id --gate            (the gate's photos)
    .venv/Scripts/python tools/fish_id_b25/embed_int8.py models/fish-id --oi              (Open Images fish)
    .venv/Scripts/python tools/fish_id_b25/embed_int8.py models/fish-id --commons-train   (Commons training photos)
    .venv/Scripts/python tools/fish_id_b25/embed_int8.py models/fish-id --t3              (Commons aquatic animals)
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


def run(items: list[tuple[str, Path]], out: Path) -> None:
    have = dict(np.load(out)) if out.exists() else {}
    todo = [(k, p) for k, p in items if k not in have]
    print(f"{len(items)} photos, {len(todo)} to embed -> {out}", flush=True)
    t0 = time.time()
    for i, (k, p) in enumerate(todo, 1):
        try:
            with Image.open(p) as im:
                have[k] = rec.embed(im).astype(np.float32)
        except Exception as exc:  # noqa: BLE001
            print("  bad", p, exc, flush=True)
        if i % 400 == 0 or i == len(todo):
            np.savez(out, **have)
            print(f"  {i}/{len(todo)}, {(time.time() - t0) / i:.2f} s a photo", flush=True)
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
