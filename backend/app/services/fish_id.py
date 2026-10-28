"""Is this the fish the angler says it is? The photo check on a catch.

A catch pin that names a guide species must come with a photo the
recognizer agrees with: a catfish posted as a largemouth bass is refused,
with the reason and the fish the photo does show. The model is BioCLIP 2
(imageomics/bioclip-2, MIT) with a classifier head fitted on openly licensed
photos, built into models/fish-id/ by app/cli/build_fish_id_model.py and
fish_id_train.py and run here with onnxruntime alone: 309 MB on disk, about
330 MB of memory, a second or two a photo on the server's two CPUs, read once
however often it is checked.

How a photo is read:
1. Two views of it, the middle square (what CLIP-style models are trained
   on) and the whole photo padded to a square (a long fish held across the
   frame loses its head and tail to the middle square). Their mean is the
   photo's vector. Mirrored copies of both were measured too: no more
   accurate (82.4% of honest claims accepted against 82.1%, the same false
   ones), at twice the time.
2. Its similarity to every class of fish_id_classes.py (guide species, fish
   with no guide, things that aren't fish) becomes a probability.
3. `check_claim` compares that with what the angler said: the same species
   (confirmed), the same group of look-alikes (accepted; the species stays
   the angler's call, and the pin says so), or not (refused).
The thresholds in `Policy` come from measuring on photos the model never
saw (app/cli/fish_id_eval.py, docs/adr/0037).
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
from app.services.fish_id_classes import BY_SLUG, CLAIM_GROUPS, GUIDE, NOT_FISH, OTHER_FISH, group_label

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

    @property
    def top(self) -> Candidate:
        return self.candidates[0]

    @property
    def fish_probability(self) -> float:
        return sum(c.probability for c in self.candidates if c.kind != NOT_FISH)

    def probability(self, slug: str) -> float:
        return next((c.probability for c in self.candidates if c.slug == slug), 0.0)

    def group_probability(self, group: str) -> float:
        return sum(c.probability for c in self.candidates if c.slug in BY_SLUG and BY_SLUG[c.slug].group == group)

    def fish(self, n: int = 3) -> list[Candidate]:
        """The likeliest fish, guide or not."""
        return [c for c in self.candidates if c.kind != NOT_FISH][:n]


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
    """Thresholds, measured (fish_id_eval.py): see docs/adr/0037."""

    # Below this much "some fish" in total, the photo isn't of a fish.
    min_fish: float = 0.5
    # The rest are shares of the fish probability, not of everything.
    # Chosen on the training set's held-out newest observations
    # (fish_id_train.py --sweep, BioCLIP 2 + head, 2026-10-27), for accuracy
    # over acceptance: there no claim of another kind of fish got through
    # (0.1% at 0.5 / 0.6) and 0.7% of look-alikes passed as the species
    # (2.5%), for 7 points fewer honest photos accepted (82% against 89%).
    # The claimed species is the likeliest fish with at least this.
    confirm: float = 0.8
    # Its group has at least this, and the likeliest fish is in the group.
    group: float = 0.8
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
    group_p = (ident.group_probability(group) if group else 0.0) / fish_p
    best_group = BY_SLUG[best.slug].group if best.slug in BY_SLUG else None
    if group and best_group == group and group_p >= policy.group:
        what = group_label(group) or _a(label)
        return Verdict(GROUP, claimed, best.slug, group_p,
                       f"Photo check: this looks like {what}. Which kind, the photo can't show, so the species is your call.")
    if best_p >= policy.contradict and best_group != group:
        if best.kind == OTHER_FISH:
            return Verdict(OTHER, claimed, best.slug, best_p,
                           f"This looks like {_a(best.label)}, not {_a(label)}. It isn't on FishEye's list yet: choose Other and name it.")
        return Verdict(MISMATCH, claimed, best.slug, best_p,
                       f"This looks like {_a(best.label)}, not {_a(label)}. Change the fish to {best.label}, or use a photo of the {label}.")
    return Verdict(UNSURE, claimed, best.slug, ident.probability(claimed) / fish_p if claim else group_p,
                   f"We couldn't confirm this is {_a(label)} from this photo. Try one that shows the whole fish, side-on, in good light.")


class FishRecognizer:
    """The image encoder, then either the zero-shot weights (the classes'
    text vectors) or, when models/fish-id/head.npz is there, the classifier
    head fitted on labelled photos (app/cli/fish_id_train.py)."""

    # How photos are read (`views`); cached photo vectors are kept per reading.
    READING = "middle+whole"

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
        # and the server has 2 GB for everything.
        opts.enable_cpu_mem_arena = False
        self._session = ort.InferenceSession(str(onnx_path), opts, providers=["CPUExecutionProvider"])
        self._text = np.load(model_dir / "text.npy")
        self._classes = json.loads((model_dir / "classes.json").read_text("utf-8"))
        self._size = int(source["image_size"])
        self._mean = np.array(source["mean"], dtype=np.float32).reshape(3, 1, 1)
        self._std = np.array(source["std"], dtype=np.float32).reshape(3, 1, 1)
        self._scale = float(source["logit_scale"])
        self._recent: dict[bytes, np.ndarray] = {}
        self._lock = threading.Lock()
        self._running = threading.Lock()
        variant = "int8" if onnx_path.name.endswith("int8.onnx") else "fp32"
        self.encoder = f"{source['repo'].split('/')[-1]}@{source['revision'][:12]}/{variant}"
        self._w, self._b = self.zero_shot_weights(), np.zeros(len(self._classes), dtype=np.float32)
        self.name = self.encoder
        head = model_dir / "head.npz"
        if use_head and head.exists():
            fitted = np.load(head)
            if str(fitted["classes_digest"]) != classes_digest():
                raise FileNotFoundError(f"{head} was fitted for another class list; refit it")
            self._w, self._b = fitted["w"], fitted["b"]
            self.name = f"{self.encoder}+head"

    def zero_shot_weights(self) -> np.ndarray:
        return (self._scale * self._text).astype(np.float32)

    # ----------------------------------------------------------- reading

    def _pixels(self, img: Image.Image) -> np.ndarray:
        arr = np.asarray(img.convert("RGB"), dtype=np.float32).transpose(2, 0, 1) / 255.0
        return (arr - self._mean) / self._std

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
        fill = tuple(int(255 * m) for m in self._mean.ravel())
        whole = Image.new("RGB", (s, s), fill)
        whole.paste(small, ((s - small.width) // 2, (s - small.height) // 2))
        return [middle, whole]

    def embed(self, img: Image.Image) -> np.ndarray:
        batch = np.stack([self._pixels(v) for v in self.views(img)])
        # One photo at a time: a run already uses every core, and two at
        # once on the server's two would just slow both and the rest of the API.
        with self._running:
            vecs = self._session.run(None, {"pixels": batch})[0]
        mean = vecs.mean(axis=0)
        return mean / np.linalg.norm(mean)

    def identify_vector(self, vec: np.ndarray) -> Identification:
        logits = self._w @ vec + self._b
        p = np.exp(logits - logits.max())
        p /= p.sum()
        order = np.argsort(-p)
        return Identification(
            tuple(
                Candidate(self._classes[i]["slug"], self._classes[i]["label"], self._classes[i]["kind"], float(p[i]))
                for i in order
            ),
            self.name,
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
