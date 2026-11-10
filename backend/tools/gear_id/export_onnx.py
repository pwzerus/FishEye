"""Export a candidate's image encoder to ONNX, compress it to int8, and check it.

    python -I export_onnx.py <model key> <out dir> <manifest.json> [n_check]

Writes <out dir>/image_fp32.onnx and image_int8.onnx (the matrix multiplies
in int8, as for the fish model), then reads n_check photos (default 40) with
the PyTorch model and both ONNX files and prints how close the vectors are
(cosine) and how long one photo (two views) takes on 2 CPU threads, the
server's two vCPUs.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.argv, extra = sys.argv[:1] + sys.argv[1:2] + ["-", "unused", "unused"], sys.argv[2:]
sys.path.insert(0, str(Path(__file__).parent))
import embed  # noqa: E402  (loads the model on import, from argv[1])

out_dir, manifest = Path(extra[0]), extra[1]
n_check = int(extra[2]) if len(extra) > 2 else 40
out_dir.mkdir(parents=True, exist_ok=True)
model, size = embed.model.float(), embed.size


class ImageEncoder(torch.nn.Module):
    def __init__(self, clip):
        super().__init__()
        self.visual = clip.visual

    def forward(self, pixels):
        v = self.visual(pixels)
        return v / v.norm(dim=-1, keepdim=True)


enc = ImageEncoder(model).cpu().eval()
fp32, int8 = out_dir / "image_fp32.onnx", out_dir / "image_int8.onnx"
with torch.no_grad():
    torch.onnx.export(enc, (torch.zeros(1, 3, size, size),), str(fp32), input_names=["pixels"],
                      output_names=["embedding"], dynamic_axes={"pixels": {0: "n"}, "embedding": {0: "n"}},
                      opset_version=17, dynamo=False)
from onnxruntime.quantization import QuantType, quantize_dynamic  # noqa: E402

quantize_dynamic(str(fp32), str(int8), weight_type=QuantType.QInt8, op_types_to_quantize=["MatMul", "Gemm"])
print(f"fp32 {fp32.stat().st_size / 1e6:.0f} MB, int8 {int8.stat().st_size / 1e6:.0f} MB")

import onnxruntime as ort  # noqa: E402

items = json.loads(Path(manifest).read_text("utf-8"))[:n_check]
opts = ort.SessionOptions()
opts.intra_op_num_threads = 2
opts.log_severity_level = 3
sessions = {name: ort.InferenceSession(str(p), opts, providers=["CPUExecutionProvider"]) for name, p in
            (("fp32", fp32), ("int8", int8))}
cos = {"fp32": [], "int8": []}
times = {"fp32": [], "int8": []}
from PIL import Image  # noqa: E402

for it in items:
    img = Image.open(it["path"]).convert("RGB")
    batch = torch.stack([embed.tensor(v) for v in embed.views(img)[:2]])
    with torch.no_grad():
        ref = enc(batch).mean(0)
        ref = (ref / ref.norm()).numpy()
    for name, sess in sessions.items():
        t = time.perf_counter()
        v = sess.run(None, {"pixels": batch.numpy()})[0].mean(0)
        times[name].append(time.perf_counter() - t)
        cos[name].append(float(v @ ref / np.linalg.norm(v)))
for name in sessions:
    print(f"{name}: cosine to PyTorch min {min(cos[name]):.4f} mean {np.mean(cos[name]):.4f}; "
          f"{np.median(times[name]):.2f} s a photo (2 views, 2 threads)")
