"""Is this the fish the angler says it is? The photo check on a catch.

A catch pin that names a guide species must come with a photo the
recognizer agrees with: a catfish posted as a largemouth bass is refused,
with the reason and the fish the photo does show. The model is BioCLIP 2.5
Huge (imageomics/bioclip-2.5-vith14, MIT) with nothing fitted on iNaturalist
photos (docs/adr/0066): its own text vectors name the fish, and only the gate
below and one number, the logit scale, were fitted, on Open Images and
Wikimedia Commons photos. Built into models/fish-id/ by tools/fish_id_b25/ and
run here with onnxruntime alone: 640 MB on disk, about 670 MB of memory,
0.8 s a photo on two laptop cores (docs/adr/0067), read once however often
it is checked.
(BioCLIP 2 with a classifier head, app/cli/build_fish_id_model.py and
fish_id_train.py, still loads the same way.)

How a photo is read:
1. Its middle square (what CLIP-style models are trained on), in one run.
   Until 2026-11-22 the whole photo padded to a square was read beside it
   and the two averaged: hardly more accurate (84.5% top-1 on 2,706 test
   photos against 83.9%) at twice the time (docs/adr/0067). A fish held out
   at the edges of a wide photo loses its head and tail to the square.
   Mirrored copies were measured too (docs/adr/0037): no more accurate, at
   twice the time.
2. Its similarity to every class of fish_id_classes.py (guide species, fish
   with no guide, things that aren't fish) becomes a probability. A second,
   separate look (models/fish-id/gate.npz) says whether the photo shows a fish
   at all: a screenshot spreads over many fish classes and looks like "some
   fish" to the first one (docs/adr/0053).
3. `check_claim` compares that with what the angler said: the same species
   (confirmed), the same group of look-alikes (accepted; the species stays
   the angler's call, and the pin says so), or not (refused).
The thresholds in `Policy` come from measuring on photos the model never
saw (app/cli/fish_id_eval.py, docs/adr/0037 and 0066).
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import threading
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from app.core.config import get_settings
from app.services.fish_id_classes import (
    BY_SLUG,
    CLAIM_GROUPS,
    GUIDE,
    GUIDED_SINCE_BUILD,
    LOOK_ALIKES,
    NOT_FISH,
    OTHER_FISH,
    SAME_FISH,
    SEA_ONLY,
    group_label,
)

logger = logging.getLogger(__name__)

CONFIRMED = "confirmed"  # the photo shows the species claimed
GROUP = "group"  # a look-alike of it; which one, the photo can't say
MISMATCH = "mismatch"  # a different guide species
OTHER = "other_fish"  # a fish with no guide
NO_FISH = "no_fish"
UNSURE = "unsure"
ACCEPTED = (CONFIRMED, GROUP)
# Photos whose vectors are kept, newest last (FishRecognizer.identify).
RECENT_PHOTOS = 32


class FishIdUnavailable(Exception):
    """The check is required but its model isn't installed."""


@dataclass(frozen=True)
class Candidate:
    slug: str
    label: str
    kind: str
    probability: float


@dataclass(frozen=True)
class Identification:
    candidates: tuple[Candidate, ...]  # every class, most likely first
    model: str
    # How sure the gate is that the photo shows a fish at all; None without one.
    gate: float | None = None

    @property
    def top(self) -> Candidate:
        return self.candidates[0]

    @property
    def fish_probability(self) -> float:
        """Nothing if the gate says there's no fish; else the share on the fish classes."""
        if self.gate is not None and self.gate < POLICY.min_photo:
            return 0.0
        return sum(c.probability for c in self.candidates if c.kind != NOT_FISH)

    def probability(self, slug: str) -> float:
        return next((c.probability for c in self.candidates if c.slug == slug), 0.0)

    def group_probability(self, group: str) -> float:
        return sum(c.probability for c in self.candidates if c.slug in BY_SLUG and BY_SLUG[c.slug].group == group)

    def fish(self, n: int = 3) -> list[Candidate]:
        """The likeliest fish, guide or not."""
        return [c for c in self.candidates if c.kind != NOT_FISH][:n]

    def inland(self) -> Identification:
        """This reading for a catch far from the sea (services/coast.py): its
        fish of the sea taken out and the rest scaled back up to a whole, as
        if the model had never known them. Measured: docs/adr/0063."""
        kept = [c for c in self.candidates if c.slug not in SEA_ONLY]
        total = sum(c.probability for c in kept)
        if total <= 0:
            return self
        return Identification(
            tuple(replace(c, probability=c.probability / total) for c in kept), f"{self.model}+inland", self.gate
        )


@dataclass(frozen=True)
class Verdict:
    status: str
    claimed: str | None
    detected: str | None  # the fish the photo shows best, when there is one
    confidence: float  # of the claim (its group, for GROUP); of `detected` otherwise
    message: str

    @property
    def accepted(self) -> bool:
        return self.status in ACCEPTED


@dataclass(frozen=True)
class Policy:
    """Thresholds, measured (fish_id_eval.py): see docs/adr/0037 and 0066."""

    # Below this much "some fish" in total, the photo isn't of a fish.
    min_fish: float = 0.5
    # Below this from the gate, neither is it (docs/adr/0053). Low on purpose:
    # refusing someone's real catch is worse than letting a strange photo by.
    min_photo: float = 0.3
    # The rest are shares of the fish probability, not of everything.
    # For BioCLIP 2.5 with no head (docs/adr/0066), chosen on Wikimedia
    # Commons photos, not iNaturalist's: at 0.8 / 0.8, the thresholds BioCLIP
    # 2 with its head used, 5 claims of another kind of fish got through
    # there; at 0.9 / 0.98, none. On 5,237 iNaturalist test photos that
    # meant 1 such claim against BioCLIP 2's 5, and the exact species
    # confirmed for 54.6% of honest claims against 51.7%.
    # The claimed species is the likeliest fish with at least this.
    confirm: float = 0.9
    # Its group has at least this, and the likeliest fish is in the group.
    group: float = 0.98
    # A different fish this sure is named as what the photo shows.
    contradict: float = 0.4


POLICY = Policy()


def _label(slug: str) -> str:
    c = BY_SLUG.get(slug)
    return c.common if c else slug.replace("-", " ").title()


def _a(label: str) -> str:
    return f"an {label}" if label[:1].lower() in "aeiou" else f"a {label}"


def check_claim(ident: Identification, claimed: str | None, policy: Policy = POLICY) -> Verdict:
    """What the photo says about the angler's claim: a guide species slug,
    or None for "Other" (any fish will do, as long as it is a fish and not
    plainly one of the guide species)."""
    # Whether there is a fish, from all classes; which fish, among fish only:
    # a catch photo is often mostly the person holding it.
    fish_p = ident.fish_probability
    if fish_p < policy.min_fish:
        return Verdict(NO_FISH, claimed, None, fish_p,
                       "We couldn't find a fish in this photo. Use one that shows the whole fish, side-on.")
    best = ident.fish(1)[0]
    best_p = best.probability / fish_p

    if claimed is None:
        if best.kind == GUIDE and best_p >= policy.confirm:
            return Verdict(MISMATCH, None, best.slug, best_p,
                           f"This looks like {_a(best.label)}. Pick it from the list instead of Other.")
        return Verdict(CONFIRMED, None, best.slug, fish_p, "There's a fish in this photo.")

    claim = BY_SLUG.get(claimed)
    group = CLAIM_GROUPS.get(claimed) or (claim.group if claim else None)
    label = claim.common if claim else _label(claimed)
    if claim is not None and best.slug == claimed and best_p >= policy.confirm:
        return Verdict(CONFIRMED, claimed, claimed, best_p, f"Photo check: this looks like {_a(label)}.")
    # A steelhead is a rainbow trout: both its names back the claim.
    if claim is not None and SAME_FISH.get(best.slug) == claimed:
        same_p = (best.probability + ident.probability(claimed)) / fish_p
        if same_p >= policy.confirm:
            return Verdict(CONFIRMED, claimed, best.slug, same_p,
                           f"Photo check: this looks like {_a(best.label)}, which is {_a(label)}.")
    group_p = (ident.group_probability(group) if group else 0.0) / fish_p
    best_group = LOOK_ALIKES.get(best.slug) or (BY_SLUG[best.slug].group if best.slug in BY_SLUG else None)
    if best.slug in LOOK_ALIKES and best_group == group:
        group_p += best_p
    if group and best_group == group and group_p >= policy.group:
        what = group_label(group) or _a(label)
        return Verdict(GROUP, claimed, best.slug, group_p,
                       f"Photo check: this looks like {what}. Which kind, the photo can't show, so the species is your call.")
    if best_p >= policy.contradict and best_group != group:
        if best.kind == OTHER_FISH and best.slug not in GUIDED_SINCE_BUILD:
            return Verdict(OTHER, claimed, best.slug, best_p,
                           f"This looks like {_a(best.label)}, not {_a(label)}. It isn't on FishEye's list yet: choose Other and name it.")
        return Verdict(MISMATCH, claimed, best.slug, best_p,
                       f"This looks like {_a(best.label)}, not {_a(label)}. Change the fish to {best.label}, or use a photo of the {label}.")
    return Verdict(UNSURE, claimed, best.slug, ident.probability(claimed) / fish_p if claim else group_p,
                   f"We couldn't confirm this is {_a(label)} from this photo. Try one that shows the whole fish, side-on, in good light.")


def middle_square(img: Image.Image, size: int) -> Image.Image:
    """The photo's middle square, `size` pixels a side: the short side scaled
    to `size`, the long one cut evenly at both ends."""
    img = img.convert("RGB")
    w, h = img.size
    scale = size / min(w, h)
    img = img.resize((max(size, round(w * scale)), max(size, round(h * scale))), Image.Resampling.BICUBIC)
    left, top = (img.width - size) // 2, (img.height - size) // 2
    return img.crop((left, top, left + size, top + size))


def load_gate(path: Path, encoder: str, reading: str) -> tuple[np.ndarray, float] | None:
    """The gate in `path`, if it was fitted on this encoder's vectors.

    One fitted on photos read another way is used all the same, with a
    warning: it is looser (two views' gate on middle squares lets 27 of 431
    unrelated photos through, against 16, docs/adr/0067), and no gate at all
    would pass screenshots as fish."""
    fitted = np.load(path)
    if str(fitted["encoder"]) != encoder:
        logger.warning("%s was fitted for another encoder; not used", path)
        return None
    # Gates written before 2026-11-22 name no reading: they read two views.
    fitted_reading = str(fitted["reading"]) if "reading" in fitted.files else "middle+whole"
    if fitted_reading != reading:
        logger.warning("%s was fitted on photos read as %s, not %s; refit it (tools/fish_id_b25/refit_gate.py)",
                       path, fitted_reading, reading)
    return fitted["w"], float(fitted["b"])


class FishRecognizer:
    """The image encoder, then either the zero-shot weights (the classes'
    text vectors) or, when models/fish-id/head.npz is there, the classifier
    head fitted on labelled photos (app/cli/fish_id_train.py)."""

    # How photos are read (`embed`); photo vectors and the gate are kept per reading.
    READING = "middle"

    def __init__(self, model_dir: Path, use_head: bool = True) -> None:
        import onnxruntime as ort

        from app.cli.build_fish_id_model import classes_digest

        candidates = [model_dir / "image_int8.onnx", model_dir / "image_fp32.onnx"]
        onnx_path = next((p for p in candidates if p.exists()), None)
        if onnx_path is None:
            raise FileNotFoundError(f"no image encoder under {model_dir}")
        source = json.loads((model_dir / "SOURCE.json").read_text("utf-8"))
        if source.get("classes_digest") != classes_digest():
            raise FileNotFoundError(f"{model_dir} was built for another class list; rebuild it")
        opts = ort.SessionOptions()
        opts.log_severity_level = 3
        # No memory arena: it keeps a photo's peak working memory for good,
        # and the server has 4 GB for everything.
        opts.enable_cpu_mem_arena = False
        self._session = ort.InferenceSession(str(onnx_path), opts, providers=["CPUExecutionProvider"])
        self._text = np.load(model_dir / "text.npy")
        self._classes = json.loads((model_dir / "classes.json").read_text("utf-8"))
        self._size = int(source["image_size"])
        self._mean = np.array(source["mean"], dtype=np.float32).reshape(3, 1, 1)
        self._std = np.array(source["std"], dtype=np.float32).reshape(3, 1, 1)
        # A model with no head may carry a logit scale fitted for it
        # (docs/adr/0066): BioCLIP 2.5's own 98.9 is surer than it is right.
        self._scale = float(source.get("calibrated_logit_scale") or source["logit_scale"])
        self._recent: dict[bytes, np.ndarray] = {}
        self._lock = threading.Lock()
        self._running = threading.Lock()
        variant = "int8" if onnx_path.name.endswith("int8.onnx") else "fp32"
        # A fine-tuned build names its tuning in SOURCE.json ("tuned"), so its
        # photo vectors (cached per encoder) and gate never mix with the original's.
        tuned = f"+{source['tuned']}" if source.get("tuned") else ""
        self.encoder = f"{source['repo'].split('/')[-1]}@{source['revision'][:12]}{tuned}/{variant}"
        self._w, self._b = self.zero_shot_weights(), np.zeros(len(self._classes), dtype=np.float32)
        self.name = self.encoder
        head = model_dir / "head.npz"
        if use_head and head.exists():
            fitted = np.load(head)
            if str(fitted["classes_digest"]) != classes_digest():
                raise FileNotFoundError(f"{head} was fitted for another class list; refit it")
            if fitted["w"].shape[1] != self._text.shape[1]:
                # Left behind by another model (BioCLIP 2's head beside BioCLIP 2.5, ADR 0066).
                logger.warning("%s was fitted for another encoder's vectors; not used", head)
            else:
                self._w, self._b = fitted["w"], fitted["b"]
                self.name = f"{self.encoder}+head"
        self._gate: tuple[np.ndarray, float] | None = None
        gate = model_dir / "gate.npz"
        if use_head and gate.exists():
            self._gate = load_gate(gate, self.encoder, self.READING)
            if self._gate is not None:
                self.name = f"{self.name}+gate"

    def zero_shot_weights(self) -> np.ndarray:
        return (self._scale * self._text).astype(np.float32)

    # ----------------------------------------------------------- reading

    def _pixels(self, img: Image.Image) -> np.ndarray:
        arr = np.asarray(img.convert("RGB"), dtype=np.float32).transpose(2, 0, 1) / 255.0
        return (arr - self._mean) / self._std

    def embed(self, img: Image.Image) -> np.ndarray:
        pixels = self._pixels(middle_square(img, self._size))[None]
        # One photo a run. A run already uses every core, so two at once on
        # the server's two would slow both and the rest of the API. And the
        # int8 encoder quantizes each run as a whole: a photo read beside
        # others gets a slightly different vector (docs/adr/0067).
        with self._running:
            vec = self._session.run(None, {"pixels": pixels})[0][0]
        return vec / np.linalg.norm(vec)

    def identify_vector(self, vec: np.ndarray) -> Identification:
        logits = self._w @ vec + self._b
        p = np.exp(logits - logits.max())
        p /= p.sum()
        order = np.argsort(-p)
        gate = None
        if self._gate is not None:
            gate = float(1 / (1 + np.exp(-(self._gate[0] @ vec + self._gate[1]))))
        return Identification(
            tuple(
                Candidate(self._classes[i]["slug"], self._classes[i]["label"], self._classes[i]["kind"], float(p[i]))
                for i in order
            ),
            self.name,
            gate,
        )

    def identify(self, photo: bytes | Image.Image) -> Identification:
        if isinstance(photo, Image.Image):
            return self.identify_vector(self.embed(photo))
        # The form checks a photo when it is chosen and the server again on
        # save: the same cleaned bytes, read once.
        key = hashlib.sha256(photo).digest()
        with self._lock:
            vec = self._recent.get(key)
        if vec is None:
            vec = self.embed(Image.open(io.BytesIO(photo)))
            with self._lock:
                self._recent[key] = vec
                while len(self._recent) > RECENT_PHOTOS:
                    self._recent.pop(next(iter(self._recent)))
        return self.identify_vector(vec)


@lru_cache(maxsize=1)
def _load(model_dir: str) -> FishRecognizer | None:
    try:
        recognizer = FishRecognizer(Path(model_dir))
    except (FileNotFoundError, ImportError) as exc:
        logger.warning("fish recognizer not available: %s", exc)
        return None
    logger.info("fish recognizer: %s", recognizer.name)
    return recognizer


def get_recognizer() -> FishRecognizer | None:
    """The recognizer, or None when the check is switched off (FISH_ID=off,
    the test suite). Raises FishIdUnavailable when it is on and its model
    isn't installed: catches that name a species wait rather than go
    unchecked."""
    settings = get_settings()
    if settings.fish_id == "off":
        return None
    recognizer = _load(settings.fish_id_model_dir)
    if recognizer is None:
        raise FishIdUnavailable("The photo check isn't available right now. Try again later.")
    return recognizer
