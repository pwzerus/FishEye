"""Build the fish recognizer's model files from BioCLIP 2 (services/fish_id.py).

The app recognizes fish with onnxruntime alone; PyTorch is needed only
here, once, on a developer's machine, in an environment of its own:

    python -m venv <env>            # a short path on Windows: onnx's test
    <env>/Scripts/pip install -r requirements-fishid-build.txt
    <env>/Scripts/python -m app.cli.build_fish_id_model      # step 1
    python -m app.cli.build_fish_id_model --quantize-only    # step 2, in the app's env

Step 1 downloads imageomics/bioclip-2 (MIT; a CLIP ViT-L/14 trained on the
tree of life, Gu et al. 2025) at a pinned commit, refusing any licence but
MIT or Apache-2.0, and writes to models/fish-id/:
- image_fp32.onnx  the image encoder (photo → unit vector);
- text.npy         one unit vector per class of services/fish_id_classes.py,
                   the mean of its prompts (no text encoder ships at all);
- classes.json     those classes, in text.npy's row order;
- SOURCE.json      repo, commit, licence, preprocessing and logit scale.
Step 2 compresses the encoder to int8 (image_int8.onnx, 309 MB), which the
app prefers. Then fit the classifier head (fish_id_train.py) and copy
models/fish-id/ to the server; nothing else is needed there.

`--model bioclip` builds the first BioCLIP instead (ViT-B/16, 89 MB, a
quarter of the time per photo, clearly less accurate: ADR 0037), for a
server too small for BioCLIP 2.

Only the model's weights are downloaded and loaded (safetensors, or
torch.load in weights_only mode): nothing executable from the repo runs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

CONFIG = "open_clip_config.json"
MODELS = Path(__file__).resolve().parents[2] / "models"
DEFAULT_DIR = MODELS / "fish-id"
# name -> (repo, reviewed commit, weights file, download folder). BioCLIP 2
# (ViT-L/14, 2025) is what the app ships; BioCLIP (ViT-B/16) is the lighter
# fallback. Both measured in ADR 0037.
SOURCES = {
    "bioclip": ("imageomics/bioclip", "ce901ab3c6a913f9e9ef94ce6d27761069f4f01c", "open_clip_pytorch_model.bin", MODELS / "bioclip-src"),
    "bioclip-2": ("imageomics/bioclip-2", "2957b322090f9cb17ae72c71981c7218a28d81e0", "open_clip_model.safetensors", MODELS / "bioclip2-src"),
}


def classes_digest() -> str:
    """Changes whenever the class list or its prompts do: the app refuses
    text vectors built for another list."""
    from app.services.fish_id_classes import CLASSES, SCENES, prompts

    text = json.dumps([[c.slug, c.kind, prompts(c)] for c in CLASSES] + [list(s) for s in SCENES])
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def build(dest: Path, model_name: str) -> int:
    try:
        import numpy as np
        import open_clip
        import torch
        from huggingface_hub import HfApi, hf_hub_download
    except ImportError:
        print("Run this in the build environment: pip install -r requirements-fishid-build.txt", file=sys.stderr)
        return 1
    from app.services.fish_id_classes import CLASSES, SCENES, prompts

    repo_id, revision, weights, source_cache = SOURCES[model_name]
    info = HfApi().model_info(repo_id, revision=revision)
    licence = (info.card_data or {}).get("license")
    licences = licence if isinstance(licence, list) else [licence]
    if not set(licences) & {"mit", "apache-2.0"}:
        print(f"Refusing: {repo_id}@{info.sha} declares licence {licence!r}, not MIT/Apache-2.0.", file=sys.stderr)
        return 1

    source_cache.mkdir(parents=True, exist_ok=True)
    config_path = Path(hf_hub_download(repo_id, CONFIG, revision=info.sha, local_dir=source_cache))
    weights_path = Path(hf_hub_download(repo_id, weights, revision=info.sha, local_dir=source_cache))
    config = json.loads(config_path.read_text(encoding="utf-8"))

    model = open_clip.model.CLIP(**config["model_cfg"])
    if weights_path.suffix == ".safetensors":
        from safetensors.torch import load_file

        state = load_file(str(weights_path))
    else:
        state = torch.load(weights_path, map_location="cpu", weights_only=True)
        state = state.get("state_dict", state)
    missing, unexpected = model.load_state_dict(state, strict=False)
    if missing or unexpected:
        print(f"Weights don't fit the model: missing {missing[:5]}, unexpected {unexpected[:5]}", file=sys.stderr)
        return 1
    model.eval()
    # Both use OpenAI CLIP's tokenizer (77 tokens), as their configs say.
    tokenizer = open_clip.get_tokenizer("ViT-B-16")

    rows, labels = [], []
    with torch.no_grad():
        for c in CLASSES:
            vecs = model.encode_text(tokenizer(prompts(c)))
            vecs = vecs / vecs.norm(dim=-1, keepdim=True)
            mean = vecs.mean(dim=0)
            rows.append((mean / mean.norm()).numpy())
            labels.append({"slug": c.slug, "kind": c.kind, "label": c.common})
        for slug, text in SCENES:
            vec = model.encode_text(tokenizer([text]))[0]
            rows.append((vec / vec.norm()).numpy())
            labels.append({"slug": slug, "kind": "not_fish", "label": text})

    dest.mkdir(parents=True, exist_ok=True)
    np.save(dest / "text.npy", np.stack(rows).astype(np.float32))
    (dest / "classes.json").write_text(json.dumps(labels, indent=1) + "\n", encoding="utf-8")

    class ImageEncoder(torch.nn.Module):
        def __init__(self, clip: torch.nn.Module) -> None:
            super().__init__()
            self.clip = clip

        def forward(self, pixels: torch.Tensor) -> torch.Tensor:
            v = self.clip.encode_image(pixels)
            return v / v.norm(dim=-1, keepdim=True)

    size = config["model_cfg"]["vision_cfg"]["image_size"]
    print("Exporting the image encoder ...")
    torch.onnx.export(
        ImageEncoder(model),
        (torch.zeros(1, 3, size, size),),
        str(dest / "image_fp32.onnx"),
        input_names=["pixels"],
        output_names=["embedding"],
        dynamic_axes={"pixels": {0: "n"}, "embedding": {0: "n"}},
        opset_version=17,
        dynamo=False,
    )
    pre = config.get("preprocess_cfg", {})
    source = {
        "repo": repo_id,
        "revision": info.sha,
        "license": licence,
        "url": f"https://huggingface.co/{repo_id}/tree/{info.sha}",
        "citation": "Stevens et al. 2024, BioCLIP: A Vision Foundation Model for the Tree of Life (CVPR).",
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "image_size": size,
        "mean": pre.get("mean", [0.48145466, 0.4578275, 0.40821073]),
        "std": pre.get("std", [0.26862954, 0.26130258, 0.27577711]),
        "logit_scale": float(model.logit_scale.exp().item()),
        "classes_digest": classes_digest(),
    }
    (dest / "SOURCE.json").write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
    print(f"Saved to {dest} ({repo_id}@{info.sha[:12]}, licence {licence}, {len(labels)} classes).")
    print("Next, in the app's environment: python -m app.cli.build_fish_id_model --quantize-only")
    return 0


def quantize(dest: Path) -> int:
    source, target = dest / "image_fp32.onnx", dest / "image_int8.onnx"
    if not source.exists():
        print(f"No {source}; build first.", file=sys.stderr)
        return 1
    from onnxruntime.quantization import QuantType, quantize_dynamic

    print("Compressing to int8 ...")
    # Matrix multiplies only: they hold nearly all of a ViT's weights, and
    # onnxruntime's CPU provider has no int8 kernel (ConvInteger) for the one
    # convolution, the patch embedding, which stays in fp32.
    quantize_dynamic(str(source), str(target), weight_type=QuantType.QInt8, op_types_to_quantize=["MatMul", "Gemm"])
    print(f"  {target.name}  ({target.stat().st_size / 1e6:.0f} MB); the app uses this one.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dest", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--model", choices=sorted(SOURCES), default="bioclip-2")
    parser.add_argument("--quantize-only", action="store_true", help="only compress an existing build")
    args = parser.parse_args(argv)
    if args.quantize_only:
        return quantize(args.dest)
    return build(args.dest, args.model)


if __name__ == "__main__":
    raise SystemExit(main())
