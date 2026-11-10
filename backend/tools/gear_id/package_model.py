"""Put the chosen gear model where the app reads it: backend/models/gear-id/.

    python -I package_model.py <model key> <gear_cache dir> <dest dir> [run tag]

Copies the per-channel int8 encoder (export_onnx.py, then per_channel=True),
writes text.npy and head.npz from train_eval.py's --save-head, SOURCE.json
(what model, which revision, its licence, how photos are read, the test
scores) and TRAINING_CREDITS.json (every photo the head was fitted on, with
its author, licence and page: CC BY asks for credit).

The run tag names the train_eval.py run whose head is packed
(results/<tag>-head.npz and -final.json), e.g. pe-core-l14-336-int8pc-open
for the head fitted with the open-catalogue photos. Without it: <key>-int8pc
when there is one, else <key>. work/labels.json must be the labels that run
was fitted on, since the credits are read from it.
"""
import csv
import hashlib
import json
import shutil
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote_plus

import numpy as np

KEY, ROOT, DEST = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
REPOS = {"pe-core-l14-336": ("timm/PE-Core-L-14-336", 336), "pe-core-b16": ("timm/PE-Core-B-16", 224)}
repo, size = REPOS[KEY]
work = ROOT / "work"
DEST.mkdir(parents=True, exist_ok=True)

from huggingface_hub import snapshot_download  # noqa: E402

# The revision embed.py used: the one in the local Hugging Face cache.
revision = Path(snapshot_download(repo, allow_patterns=["open_clip_config.json"], local_files_only=True)).name
shutil.copyfile(ROOT / "onnx" / KEY / "image_int8_pc.onnx", DEST / "image_int8.onnx")
# The head chosen with int8 vectors on val (as the server reads photos), when there is one.
if len(sys.argv) > 4:
    tag = sys.argv[4]
else:
    tag = f"{KEY}-int8pc" if (work / "results" / f"{KEY}-int8pc-head.npz").exists() else KEY
head = np.load(work / "results" / f"{tag}-head.npz")
np.save(DEST / "text.npy", head["text"].astype(np.float32))
np.savez(DEST / "head.npz", wg=head["wg"], bg=head["bg"], alpha=head["alpha"], fine_scale=head["fine_scale"],
         groups=head["groups"], members=head["members"], classes=head["classes"])
classes = [str(c) for c in head["classes"]]
(DEST / "classes.json").write_text(json.dumps([{"id": c, "kind": "not_gear" if c.startswith("x-") else "gear"}
                                               for c in classes], indent=1) + "\n", encoding="utf-8")
prompts = (work / "prompts2.json").read_bytes()
run = json.loads((work / "results" / f"{tag}-final.json").read_text("utf-8"))["group_head"]
# A PyTorch-vector score only for the runs fitted on the same labels as the PyTorch run.
pytorch = work / "results" / f"{KEY}-final.json"
same_labels = tag in (KEY, f"{KEY}-int8pc")
labels = json.loads((work / "labels.json").read_text("utf-8"))
source = {
    "repo": repo,
    "revision": revision,
    "license": "apache-2.0",
    "url": f"https://huggingface.co/{repo}/tree/{revision}",
    "citation": "Bolya et al. 2025, Perception Encoder: The best visual embeddings are not at the output of the network.",
    "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
    "image_size": size,
    "mean": [0.5, 0.5, 0.5],
    "std": [0.5, 0.5, 0.5],
    "encoder": "image encoder exported to ONNX (opset 17), MatMul/Gemm weights int8 per channel",
    "prompts_sha256": hashlib.sha256(prompts).hexdigest(),
    "head_run": tag,
    "head": {k: run[k] for k in ("lam", "scale", "epochs", "alpha")},
    "train_photos": dict(Counter(v["source"] for v in labels.values() if v["split"] == "train")),
    "val": run.get("val"),
    "test_pytorch": json.loads(pytorch.read_text("utf-8"))["group_head"]["test"] if same_labels else None,
    "test_int8": run["test"] if "int8pc" in tag else None,
}
(DEST / "SOURCE.json").write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")

meta = {r["ImageID"]: r for r in csv.DictReader(open(ROOT / "oi" / "meta.csv", encoding="utf-8"))}
commons = json.loads((ROOT / "commons_cat" / "files.json").read_text("utf-8"))
# Open-catalogue photos (fetch_candidates.py): their credit lines, by label key.
opened = {c["id"]: c for f in sorted((ROOT / "open2").glob("candidates-*.json"))
          for c in json.loads(f.read_text("utf-8"))}
CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"
PDM = "https://creativecommons.org/publicdomain/mark/1.0/"
CC_BY_2 = "https://creativecommons.org/licenses/by/2.0/"
OPEN_SOURCE = {"pd12m": "PD12M", "smithsonian": "Smithsonian Open Access",
               "yfcc": "Flickr, via the YFCC100M (OpenAI subset)", "commoncatalog": "Flickr, via CommonCatalog CC-BY"}


def open_credit(c):
    if c["source"] in ("yfcc", "commoncatalog"):  # Flickr usernames come URL-encoded
        lic, url, author = "CC BY 2.0", CC_BY_2, unquote_plus(c["author"])
    elif c["licence"] == PDM:
        lic, url, author = "Public Domain Mark 1.0", PDM, c["author"]
    elif c["licence"] in (CC0, "CC0"):
        lic, url, author = "CC0 1.0", CC0, c["author"]
    else:
        raise SystemExit(f"{c['id']}: licence {c['licence']!r} not known here")
    # PD12M's text is a machine-written caption, not a title.
    title = "" if c["source"] == "pd12m" else c["text"].split(" | ")[0].strip()[:120]
    return {"source": OPEN_SOURCE[c["source"]], "author": author, "license": lic, "license_url": url,
            "page": c["page"], "title": title}


credits = []
for key, lab in sorted(labels.items()):
    if lab["split"] != "train":
        continue
    src, raw = key.split(":", 1)
    if src == "oi":
        r = meta[raw]
        credits.append({"source": "Open Images V7", "author": r["Author"], "license": "CC BY 2.0",
                        "license_url": r["License"], "page": r["OriginalLandingURL"], "title": r["Title"][:120]})
    elif src == "commons":
        f = commons[raw]
        credits.append({"source": "Wikimedia Commons", "author": f.get("creator") or "", "license": f["licence"],
                        "page": f["page_url"], "title": f["title"]})
    elif src == "open":
        credits.append(open_credit(opened[key]))
    else:
        raise SystemExit(f"{key}: no credit line for source {src!r}")
(DEST / "TRAINING_CREDITS.json").write_text(json.dumps({
    "note": "Photos the gear model's head was fitted on. Open Images annotations: CC BY 4.0, Google LLC.",
    "photos": credits,
}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"{DEST}: {repo}@{revision[:12]}, {len(classes)} classes, {len(credits)} training photos credited, "
      f"encoder {(DEST / 'image_int8.onnx').stat().st_size / 1e6:.0f} MB")
