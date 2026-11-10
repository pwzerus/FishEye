"""What fishing gear a photo shows: the camera on /gear.

Someone holding a lure in a tackle shop, or a reel found in a garage, wants
its name and what it is for. The model is Meta's Perception Encoder
(PE-Core, Apache 2.0) with its image encoder exported to ONNX and compressed
to int8, run here with onnxruntime alone, as the fish check is. It lives in
models/gear-id/ (docs/adr/0048 says how it was built and measured). Its
classes are the items of knowledge/gear.py and nine kinds of thing that
aren't gear (a fish, water, people, food, ...).

How a photo is read:
1. Two views, as for fish (services/fish_id.py): the middle square and the
   whole photo padded to a square; their mean is the photo's vector.
2. P(group): which kind of gear it is (rod, reel, lure, hook, bait, ... or
   not gear). A linear head fitted on labelled photos, mixed with the
   model's own zero-shot answer (`alpha` of the head): the labelled photos
   say "a lure", rarely which lure, and are mostly rods and not-gear.
3. P(item | group): similarity to written descriptions of the group's items.
4. P(item) = sum over the groups an item is in of P(group) x P(item | group).
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import threading
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from app.core.config import get_settings
from app.knowledge.gear import ITEM_BY_ID

logger = logging.getLogger(__name__)

# Photos whose answers are kept, newest last: the page may ask twice.
RECENT_PHOTOS = 16


class GearIdUnavailable(Exception):
    """The camera is switched on but its model isn't installed."""


@dataclass(frozen=True)
class Policy:
    """Thresholds; see docs/adr/0048 for how they were measured."""

    # Below this much "some gear" in total, the photo isn't of gear.
    min_gear: float = 0.5
    # The likeliest item is named outright with at least this share of the
    # gear probability; below it, the page offers the likeliest few.
    sure: float = 0.6
    # Below this share the likeliest item doesn't stand out, and nothing is
    # offered: a blank or blurred picture spreads itself thin (8% at most
    # for plain colours). On the 2026-11-07 val photos it cost no right
    # answer; on test, one wrong one (docs/adr/0048).
    unclear: float = 0.2


POLICY = Policy()


@dataclass(frozen=True)
class GearCandidate:
    id: str
    probability: float  # of all gear, so the shares add up to 1


@dataclass(frozen=True)
class GearReading:
    gear_probability: float
    candidates: tuple[GearCandidate, ...]  # gear items, likeliest first
    not_gear: str | None  # the likeliest not-gear kind ("x-fish", ...)
    model: str

    @property
    def is_gear(self) -> bool:
        """Gear, and clear enough to say which: what the page answers."""
        return (self.gear_probability >= POLICY.min_gear and bool(self.candidates)
                and self.candidates[0].probability >= POLICY.unclear)

    @property
    def sure(self) -> bool:
        return self.is_gear and bool(self.candidates) and self.candidates[0].probability >= POLICY.sure


def message(reading: GearReading) -> str:
    if not reading.is_gear:
        if reading.gear_probability >= POLICY.min_gear:
            return "We couldn't tell what gear this is. Try a closer photo, with the thing filling most of it."
        if reading.not_gear == "x-fish":
            return "This looks like a fish, not fishing gear. To name a fish, add it as a catch."
        return "We couldn't find fishing gear in this photo. Try one close up, with the thing filling most of it."
    top = ITEM_BY_ID[reading.candidates[0].id].name
    if reading.sure:
        return f"This looks like: {top}."
    return "It could be one of these. Compare the photos to choose."


class GearRecognizer:
    """The image encoder, the text vectors of every class and the group
    head (models/gear-id/head.npz)."""

    def __init__(self, model_dir: Path) -> None:
        import onnxruntime as ort

        onnx_path = model_dir / "image_int8.onnx"
        if not onnx_path.exists():
            raise FileNotFoundError(f"no image encoder under {model_dir}")
        source = json.loads((model_dir / "SOURCE.json").read_text("utf-8"))
        head = np.load(model_dir / "head.npz")
        self._classes = [str(c) for c in head["classes"]]
        gear_ids = {c for c in self._classes if not c.startswith("x-")}
        if gear_ids != set(ITEM_BY_ID):
            raise FileNotFoundError(f"{model_dir} was built for another list of gear; rebuild it")
        opts = ort.SessionOptions()
        opts.log_severity_level = 3
        # No memory arena (it keeps a photo's peak working memory for good) and
        # two threads: the server has 2 vCPUs and 4 GB for everything.
        opts.enable_cpu_mem_arena = False
        opts.intra_op_num_threads = 2
        self._session = ort.InferenceSession(str(onnx_path), opts, providers=["CPUExecutionProvider"])
        self._text = np.load(model_dir / "text.npy").astype(np.float32)  # (C, D)
        self._wg = head["wg"].astype(np.float32)  # (G, D), scale included
        self._bg = head["bg"].astype(np.float32)
        self._members = head["members"].astype(np.float32)  # (G, C)
        self._alpha = float(head["alpha"])
        self._fine_scale = float(head["fine_scale"])
        self._is_gear = np.array([not c.startswith("x-") for c in self._classes])
        self._size = int(source["image_size"])
        self._mean = np.array(source["mean"], dtype=np.float32).reshape(3, 1, 1)
        self._std = np.array(source["std"], dtype=np.float32).reshape(3, 1, 1)
        self._fill = tuple(int(255 * m) for m in source["mean"])
        self._recent: dict[bytes, GearReading] = {}
        self._lock = threading.Lock()
        self._running = threading.Lock()
        self.name = f"{source['repo'].split('/')[-1]}@{source['revision'][:12]}/int8+head"

    # ----------------------------------------------------------- reading

    def views(self, img: Image.Image) -> list[Image.Image]:
        img = img.convert("RGB")
        s = self._size
        w, h = img.size
        scale = s / min(w, h)
        middle = img.resize((max(s, round(w * scale)), max(s, round(h * scale))), Image.Resampling.BICUBIC)
        left, top = (middle.width - s) // 2, (middle.height - s) // 2
        middle = middle.crop((left, top, left + s, top + s))
        scale = s / max(w, h)
        small = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.Resampling.BICUBIC)
        whole = Image.new("RGB", (s, s), self._fill)
        whole.paste(small, ((s - small.width) // 2, (s - small.height) // 2))
        return [middle, whole]

    def embed(self, img: Image.Image) -> np.ndarray:
        pixels = [(np.asarray(v, dtype=np.float32).transpose(2, 0, 1) / 255.0 - self._mean) / self._std for v in self.views(img)]
        # One photo at a time: a run already uses both of the server's cores.
        with self._running:
            vecs = self._session.run(None, {"pixels": np.stack(pixels)})[0]
        mean = vecs.mean(axis=0)
        return mean / np.linalg.norm(mean)

    def read_vector(self, vec: np.ndarray) -> GearReading:
        p = item_probabilities(vec, self._text, self._wg, self._bg, self._members, self._alpha, self._fine_scale)
        gear_p = float(p[self._is_gear].sum())
        order = np.argsort(-p)
        gear = [i for i in order if self._is_gear[i]]
        not_gear = next((self._classes[i] for i in order if not self._is_gear[i]), None)
        return GearReading(
            gear_probability=gear_p,
            candidates=tuple(GearCandidate(self._classes[i], float(p[i] / gear_p) if gear_p else 0.0) for i in gear),
            not_gear=not_gear,
            model=self.name,
        )

    def read(self, photo: bytes) -> GearReading:
        key = hashlib.sha256(photo).digest()
        with self._lock:
            known = self._recent.get(key)
        if known is not None:
            return known
        reading = self.read_vector(self.embed(Image.open(io.BytesIO(photo))))
        with self._lock:
            self._recent[key] = reading
            while len(self._recent) > RECENT_PHOTOS:
                self._recent.pop(next(iter(self._recent)))
        return reading


def item_probabilities(vec: np.ndarray, text: np.ndarray, wg: np.ndarray, bg: np.ndarray, members: np.ndarray,
                       alpha: float, fine_scale: float) -> np.ndarray:
    """P(item) for every class (gear and not), summing to 1 (see the module
    docstring). members[g, c] is 1 when class c is in group g."""

    def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
        e = np.exp(x - x.max(axis=axis, keepdims=True))
        return e / e.sum(axis=axis, keepdims=True)

    sims = fine_scale * (text @ vec)  # (C,)
    zero_shot = softmax(sims)
    zs_groups = members @ zero_shot
    zs_groups = zs_groups / zs_groups.sum()
    p_group = alpha * softmax(wg @ vec + bg) + (1 - alpha) * zs_groups  # (G,)
    within = np.where(members > 0, sims[None, :], -np.inf)  # (G, C)
    within = softmax(within, axis=1)
    return p_group @ within


@lru_cache(maxsize=1)
def _load(model_dir: str) -> GearRecognizer | None:
    try:
        recognizer = GearRecognizer(Path(model_dir))
    except (FileNotFoundError, ImportError, KeyError) as exc:
        logger.warning("gear recognizer not available: %s", exc)
        return None
    logger.info("gear recognizer: %s", recognizer.name)
    return recognizer


def installed() -> bool:
    """Whether the camera can answer here, without loading the model: the
    page shows the camera only then (GET /api/gear)."""
    settings = get_settings()
    model_dir = Path(settings.gear_id_model_dir)
    return settings.gear_id != "off" and all(
        (model_dir / name).exists() for name in ("image_int8.onnx", "head.npz", "text.npy", "SOURCE.json"))


def get_recognizer() -> GearRecognizer | None:
    """The recognizer, or None when the camera is switched off (GEAR_ID=off,
    the test suite). Raises GearIdUnavailable when it is on and its model
    isn't installed."""
    settings = get_settings()
    if settings.gear_id == "off":
        return None
    recognizer = _load(settings.gear_id_model_dir)
    if recognizer is None:
        raise GearIdUnavailable("The gear camera isn't available right now. Try again later.")
    return recognizer
