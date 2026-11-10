"""Photo and text vectors for one candidate model, on the GPU when there is one.

    python -I embed.py <model key> <manifest.json> <prompts.json> <out.npz>

manifest.json: [{"id": ..., "path": ..., "rotate": 0}, ...]
prompts.json:  {"class id": ["a photo of ...", ...], ...}

Each photo is read the way the fish check reads one (app/services/fish_id.py):
the middle square and the whole photo padded to a square, at the model's
own size and normalisation. Their mirror images are kept too, as extra
training views. Saved: ids, vecs (N, 4, D) float16 in the order middle,
whole, middle mirrored, whole mirrored, all unit length; text (C, D) with
the class order in classes.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import open_clip
import torch
from PIL import Image, ImageOps

KEY, MANIFEST, PROMPTS, OUT = sys.argv[1:5]
TEXT_ONLY = MANIFEST == "-"  # text vectors only, for trying other prompts
BIOCLIP2 = Path(__file__).resolve().parents[2] / "models" / "bioclip2-src"  # build_fish_id_model.py puts it there
MODELS = {
    "b32": ("ViT-B-32", "laion2b_s34b_b79k"),
    "siglip2-b16-256": ("ViT-B-16-SigLIP2-256", "webli"),
    "siglip2-l16-384": ("ViT-L-16-SigLIP2-384", "webli"),
    "siglip2-so400m-384": ("ViT-SO400M-16-SigLIP2-384", "webli"),
    "pe-core-b16": ("PE-Core-B-16", "meta"),
    "pe-core-l14-336": ("PE-Core-L-14-336", "meta"),
}
dev = "cuda" if torch.cuda.is_available() else "cpu"


DTYPES = {"F32": torch.float32, "F16": torch.float16, "BF16": torch.bfloat16, "I64": torch.int64, "I32": torch.int32}


def read_safetensors(path, params, chunk=64 << 20):
    """Copy a .safetensors file into params (tensors on the GPU) with plain
    reads, 64 MB at a time. safetensors' own loader maps the whole file
    copy-on-write, which Windows charges in full against its page file."""
    import struct

    with open(path, "rb") as fh:
        n = struct.unpack("<Q", fh.read(8))[0]
        header = json.loads(fh.read(n))
        base = 8 + n
        found = set()
        for k, info in header.items():
            if k == "__metadata__" or k not in params:
                continue
            found.add(k)
            start, end = info["data_offsets"]
            dtype = DTYPES[info["dtype"]]
            flat = params[k].view(-1)
            size = torch.tensor([], dtype=dtype).element_size()
            assert (end - start) // size == flat.numel(), (k, info["shape"], tuple(params[k].shape))
            fh.seek(base + start)
            done = 0
            while done < flat.numel():
                count = min(chunk // size, flat.numel() - done)
                buf = bytearray(fh.read(count * size))
                flat[done:done + count].copy_(torch.frombuffer(buf, dtype=dtype).to(flat.device, flat.dtype))
                done += count
    return found | {k for k in header if k != "__metadata__"}


def load(key):
    if key == "bioclip2":
        cfg = json.loads((BIOCLIP2 / "open_clip_config.json").read_text("utf-8"))
        model = open_clip.model.CLIP(**cfg["model_cfg"])
        from safetensors.torch import load_file

        missing, unexpected = model.load_state_dict(load_file(str(BIOCLIP2 / "open_clip_model.safetensors")), strict=False)
        assert not missing and not unexpected, (missing[:3], unexpected[:3])
        pre = cfg.get("preprocess_cfg", {})
        mean = pre.get("mean", open_clip.OPENAI_DATASET_MEAN)
        std = pre.get("std", open_clip.OPENAI_DATASET_STD)
        tok = open_clip.get_tokenizer("ViT-B-16")
        size = cfg["model_cfg"]["vision_cfg"]["image_size"]
        return model, tok, size, mean, std
    name, pretrained = MODELS[key]
    # Built straight on the GPU and filled one tensor at a time: open_clip's
    # own loader holds the model and the whole checkpoint in RAM at once
    # (9 GB for SO400M), more than Windows will commit here.
    from huggingface_hub import hf_hub_download

    repo = open_clip.get_pretrained_cfg(name, pretrained)["hf_hub"].strip("/")
    weights = hf_hub_download(repo, "open_clip_model.safetensors")
    with torch.device(dev):
        model = open_clip.create_model(name, pretrained=None, device=dev)
    params = model.state_dict()
    names = read_safetensors(weights, params)
    missing = set(params) - names
    assert not {k for k in missing if "attn_mask" not in k}, sorted(missing)[:5]
    print(f"  loaded {len(names & set(params))} tensors from {Path(weights).name}", flush=True)
    tok = open_clip.get_tokenizer(name)
    v = model.visual
    size = v.image_size if isinstance(v.image_size, int) else v.image_size[0]
    pre = getattr(v, "preprocess_cfg", {}) or {}
    mean = pre.get("mean", getattr(v, "image_mean", None) or open_clip.OPENAI_DATASET_MEAN)
    std = pre.get("std", getattr(v, "image_std", None) or open_clip.OPENAI_DATASET_STD)
    return model, tok, size, mean, std


model, tok, size, mean, std = load(KEY)
model = model.to(dev).eval()
half = dev == "cuda"
if half:
    model = model.half()
mean_t = torch.tensor(mean).view(3, 1, 1)
std_t = torch.tensor(std).view(3, 1, 1)
fill = tuple(int(255 * m) for m in mean)


def views(img):
    w, h = img.size
    s = size
    scale = s / min(w, h)
    mid = img.resize((max(s, round(w * scale)), max(s, round(h * scale))), Image.Resampling.BICUBIC)
    left, top = (mid.width - s) // 2, (mid.height - s) // 2
    mid = mid.crop((left, top, left + s, top + s))
    scale = s / max(w, h)
    small = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.Resampling.BICUBIC)
    whole = Image.new("RGB", (s, s), fill)
    whole.paste(small, ((s - small.width) // 2, (s - small.height) // 2))
    return [mid, whole, ImageOps.mirror(mid), ImageOps.mirror(whole)]


def tensor(img):
    arr = torch.from_numpy(np.asarray(img, dtype=np.float32).transpose(2, 0, 1) / 255.0)
    return (arr - mean_t) / std_t


def main():
    items = [] if TEXT_ONLY else json.loads(Path(MANIFEST).read_text("utf-8"))
    # --reuse old.npz: photos already in it (same model) keep their vectors.
    old_ids, old_vecs = [], None
    if "--reuse" in sys.argv and Path(sys.argv[sys.argv.index("--reuse") + 1]).exists():
        prev = np.load(sys.argv[sys.argv.index("--reuse") + 1])
        want = {it["id"] for it in items}
        keep = [n for n, i in enumerate(prev["ids"]) if str(i) in want]
        old_ids, old_vecs = [str(prev["ids"][n]) for n in keep], prev["vecs"][keep]
        items = [it for it in items if it["id"] not in set(old_ids)]
        print(f"  reusing {len(old_ids)} photos' vectors, {len(items)} to read", flush=True)
    prompts = json.loads(Path(PROMPTS).read_text("utf-8"))
    t0 = time.time()
    with torch.no_grad():
        classes, text = list(prompts), []
        for c in classes:
            t = model.encode_text(tok(prompts[c]).to(dev)).float()
            t = t / t.norm(dim=-1, keepdim=True)
            m = t.mean(0)
            text.append((m / m.norm()).cpu().numpy())
        vecs, ids, batch, batch_ids = [], [], [], []

        def flush():
            x = torch.stack(batch).to(dev)
            if half:
                x = x.half()
            v = model.encode_image(x).float()
            v = v / v.norm(dim=-1, keepdim=True)
            vecs.append(v.view(-1, 4, v.shape[-1]).cpu().numpy().astype(np.float16))
            ids.extend(batch_ids)
            batch.clear()
            batch_ids.clear()

        for n, it in enumerate(items, 1):
            img = Image.open(it["path"]).convert("RGB")
            if it.get("rotate"):
                img = img.rotate(it["rotate"], expand=True)
            batch.extend(tensor(v) for v in views(img))
            batch_ids.append(it["id"])
            if len(batch_ids) == 16:
                flush()
            if n % 500 == 0:
                print(f"  {n}/{len(items)} photos, {time.time() - t0:.0f}s", flush=True)
        if batch_ids:
            flush()
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    if TEXT_ONLY:
        np.savez(OUT, text=np.stack(text).astype(np.float32), classes=np.array(classes))
        print(f"{KEY}: text only, {len(classes)} classes")
        return
    all_vecs = [old_vecs] if old_vecs is not None and len(old_ids) else []
    all_vecs += vecs
    np.savez(OUT, ids=np.array(old_ids + ids), vecs=np.concatenate(all_vecs), text=np.stack(text).astype(np.float32),
             classes=np.array(classes), size=size)
    ids = old_ids + ids
    print(f"{KEY}: {len(ids)} photos x 4 views, {len(classes)} classes, dim {all_vecs[0].shape[-1]}, "
          f"{time.time() - t0:.0f}s on {dev}")


if __name__ == "__main__":
    main()
