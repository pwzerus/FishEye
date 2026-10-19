"""Download the embedding model semantic retrieval uses (docs/adr/0025).

    python -m app.cli.fetch_embedding_model

Fetches intfloat/multilingual-e5-small (MIT) from Hugging Face into
backend/models/multilingual-e5-small/: the ONNX export of the model, its
tokenizer, and the model card. Nothing executable is downloaded: no Python
files, and the app loads the model with onnxruntime, not trust_remote_code.

The exact commit is pinned and written to SOURCE.json with the license the
model card declares, so what is deployed can always be traced back to the
files that were reviewed. Re-running with the same revision is a no-op.

After downloading, the model is compressed to int8 (onnx/model_int8.onnx),
which the app prefers: 118 MB instead of 470 MB, about half the memory, and
the same eval results (ADR 0025). `--quantize-only` does just that step for
a model already downloaded.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ID = "intfloat/multilingual-e5-small"
# Preferred file first. model.onnx is the full-precision export; the app
# never needs anything else from the onnx/ folder.
ONNX_CANDIDATES = ("onnx/model.onnx",)
SUPPORT_FILES = ("tokenizer.json", "config.json", "README.md")
DEFAULT_DIR = Path(__file__).resolve().parents[2] / "models" / "multilingual-e5-small"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dest", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--revision", default=None, help="commit sha; default: the current main")
    parser.add_argument("--quantize-only", action="store_true", help="only compress an existing download")
    args = parser.parse_args(argv)
    if args.quantize_only:
        return quantize(args.dest)

    try:
        from huggingface_hub import HfApi, hf_hub_download
    except ImportError:
        print("Install the semantic extras first: pip install -r requirements-semantic.txt", file=sys.stderr)
        return 1

    info = HfApi().model_info(REPO_ID, revision=args.revision, files_metadata=True)
    license_ = info.card_data.get("license") if info.card_data else None
    if license_ not in ("mit", "apache-2.0"):
        print(f"Refusing: {REPO_ID}@{info.sha} declares license {license_!r}, not MIT/Apache-2.0.", file=sys.stderr)
        return 1

    sizes = {s.rfilename: s.size for s in info.siblings or []}
    onnx_file = next((f for f in ONNX_CANDIDATES if f in sizes), None)
    if onnx_file is None:
        found = sorted(f for f in sizes if f.endswith(".onnx"))
        print(f"No {ONNX_CANDIDATES} in {REPO_ID}@{info.sha}; ONNX files there: {found}", file=sys.stderr)
        return 1

    args.dest.mkdir(parents=True, exist_ok=True)
    files = [onnx_file, *SUPPORT_FILES]
    for name in files:
        size = sizes.get(name)
        print(f"  {name}  ({(size or 0) / 1e6:.0f} MB)")
        hf_hub_download(REPO_ID, name, revision=info.sha, local_dir=args.dest)

    source = {
        "repo": REPO_ID,
        "revision": info.sha,
        "license": license_,
        "url": f"https://huggingface.co/{REPO_ID}/tree/{info.sha}",
        "files": files,
        "downloaded_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (args.dest / "SOURCE.json").write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
    print(f"Saved to {args.dest} ({REPO_ID}@{info.sha[:12]}, license {license_}).")
    return quantize(args.dest)


def quantize(dest: Path) -> int:
    source, target = dest / "onnx" / "model.onnx", dest / "onnx" / "model_int8.onnx"
    if not source.exists():
        print(f"No {source}; download first.", file=sys.stderr)
        return 1
    try:
        from onnxruntime.quantization import QuantType, quantize_dynamic
    except ImportError:
        print("Install the semantic extras first: pip install -r requirements-semantic.txt", file=sys.stderr)
        return 1
    print("Compressing to int8 ...")
    quantize_dynamic(str(source), str(target), weight_type=QuantType.QInt8)
    print(f"  {target.name}  ({target.stat().st_size / 1e6:.0f} MB); the app uses this one.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
