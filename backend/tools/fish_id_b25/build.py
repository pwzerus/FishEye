"""BioCLIP 2.5 Huge (imageomics/bioclip-2.5-vith14, MIT) for the fish photo
check: its text vectors for every class, and its image encoder as ONNX, in
the layout app/services/fish_id.py reads (docs/adr/0066).

    python -I tools/fish_id_b25/build.py text       (GPU env: torch, open_clip, safetensors)
    python -I tools/fish_id_b25/build.py export     (GPU env: fp32 ONNX, weights in external files)
    .venv/Scripts/python tools/fish_id_b25/build.py quantize   (backend env: int8, MatMul/Gemm, per channel)

Run from backend/. The weights are read from models/bioclip25-src/
(open_clip_config.json and open_clip_model.safetensors from the revision
below, downloaded once); everything is written to models/fish-id-b25/, which
becomes models/fish-id/ once its gate is fitted (fit_gate.py). Set HF_HOME,
TEMP and TMP off a full system disk.
"""
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

B = Path(__file__).resolve().parents[2]
SRC = B / "models/bioclip25-src"
DEST = B / "models/fish-id-b25"
REPO = "imageomics/bioclip-2.5-vith14"
REVISION = "6e3d04e3d6522012c88181085c5ae666e14c45cd"


def load():
    import open_clip
    import torch
    from safetensors import safe_open

    cfg = json.loads((SRC / "open_clip_config.json").read_text("utf-8"))
    model = open_clip.model.CLIP(**cfg["model_cfg"])
    # safetensors.torch.load_file crashed with this torch on Windows; numpy reads the file fine.
    with safe_open(str(SRC / "open_clip_model.safetensors"), framework="np") as f:
        state = {k: torch.from_numpy(f.get_tensor(k)) for k in f.keys()}
    missing, unexpected = model.load_state_dict(state, strict=False)
    assert not missing and not unexpected, (missing[:3], unexpected[:3])
    return model.eval(), cfg


def text() -> None:
    import open_clip
    import numpy as np
    import torch

    sys.path.insert(0, str(B))
    from app.cli.build_fish_id_model import classes_digest
    from app.services.fish_id_classes import CLASSES, SCENES, prompts

    model, cfg = load()
    model = model.cuda()
    tokenizer = open_clip.get_tokenizer("ViT-B-16")  # OpenAI CLIP's, as the config's vocab says
    rows, labels = [], []
    with torch.no_grad():
        for c in CLASSES:
            v = model.encode_text(tokenizer(prompts(c)).cuda()).float()
            v = v / v.norm(dim=-1, keepdim=True)
            m = v.mean(dim=0)
            rows.append((m / m.norm()).cpu().numpy())
            labels.append({"slug": c.slug, "kind": c.kind, "label": c.common})
        for slug, phrase in SCENES:
            v = model.encode_text(tokenizer([phrase]).cuda())[0].float()
            rows.append((v / v.norm()).cpu().numpy())
            labels.append({"slug": slug, "kind": "not_fish", "label": phrase})
    DEST.mkdir(parents=True, exist_ok=True)
    np.save(DEST / "text.npy", np.stack(rows).astype(np.float32))
    (DEST / "classes.json").write_text(json.dumps(labels, indent=1) + "\n", encoding="utf-8")
    pre = cfg.get("preprocess_cfg", {})
    source_path = DEST / "SOURCE.json"
    old = json.loads(source_path.read_text("utf-8")) if source_path.exists() else {}
    source = {
        "repo": REPO,
        "revision": REVISION,
        "license": ["mit"],
        "url": f"https://huggingface.co/{REPO}/tree/{REVISION}",
        "citation": "Gu et al. 2025, BioCLIP 2: Emergent Properties from Scaling Hierarchical Contrastive Learning; BioCLIP 2.5 Huge model card.",
        "built_at": old.get("built_at") or datetime.now(UTC).isoformat(timespec="seconds"),
        "image_size": int(cfg["model_cfg"]["vision_cfg"]["image_size"]),
        "mean": pre.get("mean"),
        "std": pre.get("std"),
        "logit_scale": float(model.logit_scale.exp().item()),
        "classes_digest": classes_digest(),
        "text_built_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    # The logit scale fitted for this model (fit_gate.py --write) survives a rebuild of the text.
    for key in ("calibrated_logit_scale", "calibrated_on"):
        if key in old:
            source[key] = old[key]
    source_path.write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")
    print("text", len(rows), "classes, logit scale", round(source["logit_scale"], 2), flush=True)


def export() -> None:
    import torch

    model, cfg = load()
    size = int(cfg["model_cfg"]["vision_cfg"]["image_size"])

    class ImageEncoder(torch.nn.Module):
        def __init__(self, v: torch.nn.Module) -> None:
            super().__init__()
            self.v = v

        def forward(self, pixels: torch.Tensor) -> torch.Tensor:
            e = self.v(pixels)
            return e / e.norm(dim=-1, keepdim=True)

    enc = ImageEncoder(model.visual.eval()).eval()
    out = DEST / "fp32"
    out.mkdir(parents=True, exist_ok=True)
    # ViT-H is past ONNX's 2 GB single-file limit: the weights go in files beside it.
    torch.onnx.export(
        enc, (torch.zeros(1, 3, size, size),), str(out / "image_fp32.onnx"),
        input_names=["pixels"], output_names=["embedding"],
        dynamic_axes={"pixels": {0: "n"}, "embedding": {0: "n"}}, opset_version=17, dynamo=False,
    )
    print("exported", out / "image_fp32.onnx", flush=True)


def quantize() -> None:
    from onnxruntime.quantization import QuantType, quantize_dynamic

    quantize_dynamic(
        str(DEST / "fp32/image_fp32.onnx"), str(DEST / "image_int8.onnx"),
        weight_type=QuantType.QInt8, op_types_to_quantize=["MatMul", "Gemm"], per_channel=True,
    )
    print("int8", round((DEST / "image_int8.onnx").stat().st_size / 1e6), "MB", flush=True)


if __name__ == "__main__":
    {"text": text, "export": export, "quantize": quantize}[sys.argv[1]]()
