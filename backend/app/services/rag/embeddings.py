"""Sentence embeddings for semantic retrieval (docs/adr/0025).

intfloat/multilingual-e5-small (MIT), run locally with onnxruntime on the
CPU. Fetched once by `python -m app.cli.fetch_embedding_model`; the app
itself never calls Hugging Face or any other service to embed text.

E5 is trained for asymmetric search, so questions are encoded as
"query: ..." and guide passages as "passage: ...". Vectors are mean-pooled
over the real tokens and L2-normalised, so a dot product is the cosine.

Everything here is optional. Without the semantic requirements or the model
files, `load_embedder()` returns None and Ask uses keyword search alone.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import numpy as np

log = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parents[3] / "models" / "multilingual-e5-small"
MAX_TOKENS = 512  # the model's limit; every guide passage is far shorter
BATCH = 16


class Embedder(Protocol):
    """Unit-length vectors, one row per text. `kind` is "query" or "passage"."""

    name: str

    def encode(self, texts: list[str], kind: str) -> np.ndarray: ...


class E5Embedder:
    def __init__(self, model_dir: Path) -> None:
        import onnxruntime as ort
        from tokenizers import Tokenizer

        # The int8 file (fetch_embedding_model compresses to it) when present:
        # half the memory, same eval results (ADR 0025).
        candidates = [model_dir / "onnx" / "model_int8.onnx", model_dir / "onnx" / "model.onnx"]
        onnx_path = next((p for p in candidates if p.exists()), None)
        if onnx_path is None:
            raise FileNotFoundError(f"no ONNX model under {model_dir / 'onnx'}")
        opts = ort.SessionOptions()
        opts.log_severity_level = 3
        self._session = ort.InferenceSession(str(onnx_path), opts, providers=["CPUExecutionProvider"])
        self._inputs = {i.name for i in self._session.get_inputs()}
        self._tok = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        self._tok.enable_truncation(MAX_TOKENS)
        self._tok.enable_padding()
        source = model_dir / "SOURCE.json"
        revision = json.loads(source.read_text("utf-8")).get("revision", "") if source.exists() else ""
        variant = "int8" if onnx_path.name == "model_int8.onnx" else "fp32"
        self.name = f"multilingual-e5-small@{revision[:12] or 'unknown'}/{variant}"

    def encode(self, texts: list[str], kind: str) -> np.ndarray:
        import numpy as np

        prefix = "query: " if kind == "query" else "passage: "
        out = []
        for start in range(0, len(texts), BATCH):
            batch = self._tok.encode_batch([prefix + t for t in texts[start : start + BATCH]])
            ids = np.array([e.ids for e in batch], dtype=np.int64)
            mask = np.array([e.attention_mask for e in batch], dtype=np.int64)
            feeds = {"input_ids": ids, "attention_mask": mask}
            if "token_type_ids" in self._inputs:
                feeds["token_type_ids"] = np.zeros_like(ids)
            hidden = self._session.run(None, feeds)[0]  # (batch, tokens, dim)
            m = mask[:, :, None].astype(np.float32)
            pooled = (hidden * m).sum(axis=1) / np.clip(m.sum(axis=1), 1e-9, None)
            out.append(pooled / np.linalg.norm(pooled, axis=1, keepdims=True))
        return np.vstack(out).astype(np.float32)


def load_embedder(model_dir: Path = MODEL_DIR) -> E5Embedder | None:
    """The local model, or None (logged once) when it isn't installed."""
    if not (model_dir / "tokenizer.json").exists():
        log.info("semantic retrieval off: no model at %s (python -m app.cli.fetch_embedding_model)", model_dir)
        return None
    try:
        return E5Embedder(model_dir)
    except ImportError:
        log.info("semantic retrieval off: pip install -r requirements-semantic.txt")
    except Exception:  # a corrupt or partial download must not take Ask down
        log.exception("semantic retrieval off: could not load %s", model_dir)
    return None


def passage_vectors(embedder: Embedder, texts: list[str], cache_dir: Path | None = MODEL_DIR) -> np.ndarray:
    """Vectors for the guide passages, cached on disk by content.

    The guides only change with a deploy, so the cache key is the model plus
    every passage's text: any edit to a guide makes a new key and the stale
    file is simply never read again."""
    import numpy as np

    key = hashlib.sha256("\x00".join([embedder.name, *texts]).encode("utf-8")).hexdigest()[:16]
    path = cache_dir / f"passages-{key}.npy" if cache_dir else None
    if path and path.exists():
        vecs = np.load(path)
        if vecs.shape[0] == len(texts):
            return vecs
    vecs = embedder.encode(texts, kind="passage")
    if path:
        try:
            np.save(path, vecs)
        except OSError:
            log.warning("could not cache passage vectors at %s", path)
    return vecs
