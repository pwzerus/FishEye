"""Fit the fish recognizer's classifier head on the training photos.

    python -m app.cli.fish_id_train        # writes models/fish-id/head.npz
    python -m app.cli.fish_id_eval         # then measure on the test set

Zero-shot BioCLIP tells families apart well and look-alike species poorly
(a largemouth bass comes out as a spotted bass more often than not;
docs/adr/0037). A linear head on its photo vectors, fitted on labelled
photos, fixes most of that. It starts from the zero-shot weights (the text
vectors, times the logit scale) and is pulled back towards them while it
learns (L2 to the start, strength `--pull`), so a class with few photos
stays close to what BioCLIP already knew. Classes with no photos (not a
fish, scenes) keep their zero-shot weights exactly.

Photos: fishid_cache/train/ (fish_id_photos.py --train; 2015-2023, other
observations than the test set's). Each species counts equally, however
many photos it has. The pull (and, with --sweep, the check's thresholds)
are chosen on each species' newest fifth of training observations, held
out, never on the test set. The photos' creators are credited in
models/fish-id/TRAINING_CREDITS.json, which ships with the head.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import replace
from pathlib import Path

import numpy as np

from app.cli.build_fish_id_model import classes_digest
from app.cli.fish_id_eval import evaluate, pct, vectors
from app.services.fish_id import CONFIRMED, POLICY, FishRecognizer

TRAIN = Path("fishid_cache/train")


def fit(x: np.ndarray, y: np.ndarray, w0: np.ndarray, trainable: np.ndarray, pull: float, steps: int = 800, lr: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """Multinomial logistic regression by full-batch Adam, from w0, with
    (pull/2)·|W − w0|² on the trainable rows; the others stay w0."""
    n_cls = w0.shape[0]
    counts = np.bincount(y, minlength=n_cls).astype(np.float64)
    sample_w = (1.0 / counts[y]) / np.count_nonzero(counts)  # each class weighs the same in total
    w, b = w0.copy(), np.zeros(n_cls)
    m_w, v_w, m_b, v_b = (np.zeros_like(w), np.zeros_like(w), np.zeros(n_cls), np.zeros(n_cls))
    onehot = np.eye(n_cls)[y]
    mask = trainable[:, None].astype(np.float64)
    for t in range(1, steps + 1):
        logits = x @ w.T + b
        logits -= logits.max(axis=1, keepdims=True)
        p = np.exp(logits)
        p /= p.sum(axis=1, keepdims=True)
        g = (p - onehot) * sample_w[:, None]
        grad_w = (g.T @ x + pull * (w - w0)) * mask
        grad_b = g.sum(axis=0) * trainable
        for param, grad, m, v in ((w, grad_w, m_w, v_w), (b, grad_b, m_b, v_b)):
            m *= 0.9
            m += 0.1 * grad
            v *= 0.999
            v += 0.001 * grad**2
            param -= lr * 0.01 * (m / (1 - 0.9**t)) / (np.sqrt(v / (1 - 0.999**t)) + 1e-8)
    return w.astype(np.float32), b.astype(np.float32)


def accuracy(x: np.ndarray, y: np.ndarray, w: np.ndarray, b: np.ndarray) -> float:
    return float(((x @ w.T + b).argmax(axis=1) == y).mean())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model-dir", type=Path, default=Path("models/fish-id"))
    parser.add_argument("--pull", type=float, default=None, help="skip the search and use this")
    parser.add_argument("--sweep", action="store_true", help="also score the check's thresholds on the held-out fifth")
    args = parser.parse_args(argv)

    recognizer = FishRecognizer(args.model_dir, use_head=False)
    classes = json.loads((args.model_dir / "classes.json").read_text("utf-8"))
    index = {c["slug"]: i for i, c in enumerate(classes)}
    photos = [p for p in json.loads((TRAIN / "manifest.json").read_text("utf-8"))["photos"] if p["slug"] in index]
    x = vectors(recognizer, photos, TRAIN).astype(np.float64)
    y = np.array([index[p["slug"]] for p in photos])
    w0 = recognizer.zero_shot_weights().astype(np.float64)
    trainable = np.zeros(len(classes), dtype=bool)
    trainable[np.unique(y)] = True

    # Held out: each class's newest fifth of observations (iNaturalist numbers
    # them in order). Like the test set, they are later than what the head
    # learns from, so the pull and thresholds are chosen for photos to come.
    numbers = np.array([int(re.search(r"(\d+)\D*$", p["observation"]).group(1)) for p in photos])
    held = np.zeros(len(y), dtype=bool)
    for cls in np.unique(y):
        idx = np.flatnonzero(y == cls)
        held[idx[numbers[idx] >= np.quantile(numbers[idx], 0.8)]] = True
    print(f"{len(y)} training photos, {trainable.sum()} classes; zero-shot on the held-out fifth: "
          f"{accuracy(x[held], y[held], w0, np.zeros(len(classes))):.3f}")
    # The data term is a mean over photos (about 1), the pull a sum over
    # 512 dimensions of every class: useful pulls are small.
    pulls = [args.pull] if args.pull is not None else [1e-5, 3e-5, 1e-4, 3e-4, 1e-3]
    best = (-1.0, pulls[0])
    for pull in pulls:
        w, b = fit(x[~held], y[~held], w0, trainable, pull)
        acc = accuracy(x[held], y[held], w, b)
        print(f"  pull {pull:<5} held-out accuracy {acc:.3f}")
        best = max(best, (acc, pull))
    pull = best[1]
    if args.sweep:
        # The thresholds of services/fish_id.Policy, judged on the held-out
        # fifth by a head fitted without it: never on the test set.
        w, b = fit(x[~held], y[~held], w0, trainable, pull)
        recognizer._w, recognizer._b = w, b
        held_photos = [p for p, h in zip(photos, held) if h]
        # `contradict` only changes which refusal is said, not whether.
        print("confirm group | true accepted  other-group accepted  same-group confirmed  no-guide other-group accepted")
        for confirm in (0.5, 0.6, 0.7, 0.8):
            for group in (0.6, 0.7, 0.8, 0.9):
                pol = replace(POLICY, confirm=confirm, group=group)
                r = evaluate(recognizer, held_photos, x[held].astype(np.float32), pol)["r"]
                print(
                    f"{confirm:.2f} {group:.2f} | {pct(r['true']['accepted'], r['true']['claims']):>6} "
                    f"{pct(r['other_group']['accepted'], r['other_group']['claims']):>6} "
                    f"{pct(r['same_group'][CONFIRMED], r['same_group']['claims']):>6} "
                    f"{pct(r['lookalike_other_group']['accepted'], r['lookalike_other_group']['claims']):>6}"
                )
    w, b = fit(x, y, w0, trainable, pull)
    np.savez(args.model_dir / "head.npz", w=w, b=b, pull=np.float32(pull), classes_digest=np.array(classes_digest()))
    credits = [
        {"observation": p["observation"], "creator": p["creator"], "licence": p["licence"]}
        for p in photos
    ]
    (args.model_dir / "TRAINING_CREDITS.json").write_text(
        json.dumps(
            {
                "about": "Photos the classifier head was fitted on: research-grade iNaturalist observations "
                "via GBIF, CC0 1.0 or CC BY 4.0. With thanks to their creators.",
                "photos": credits,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"head.npz written (pull {pull}, {len(y)} photos); credits in TRAINING_CREDITS.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
