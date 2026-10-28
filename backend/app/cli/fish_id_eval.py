"""Measure the photo check on photos the model never saw (fish_id_photos.py).

    python -m app.cli.fish_id_eval                 # report to stdout
    python -m app.cli.fish_id_eval --out ../reports/fish-id-eval.md

Every photo is checked against every claim an angler could make, through
the app's own `check_claim`, so what is measured is what the app does:
- a true claim: accepted as the species (confirmed), accepted as its group
  of look-alikes, or refused (the angler has to retake the photo);
- a false claim of another group (a catfish posted as a bass): must be
  refused. This is the number that matters most;
- a false claim within the group (a spotted bass posted as a largemouth):
  accepted as the group is allowed, as the species is an error;
- photos of fish with no guide (walleye, gar…), claimed as any guide
  species: must be refused.
Photo vectors are cached per model in fishid_cache/, so trying another
policy costs seconds.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image

from app.services.fish_id import (
    CONFIRMED,
    GROUP,
    MISMATCH,
    NO_FISH,
    OTHER,
    POLICY,
    UNSURE,
    FishRecognizer,
    Policy,
    check_claim,
)
from app.services.fish_id_classes import BY_SLUG, CLAIM_GROUPS, GUIDE

CACHE = Path("fishid_cache")
CLAIMS = [c.slug for c in BY_SLUG.values() if c.kind == GUIDE] + list(CLAIM_GROUPS)


def _group(slug: str) -> str | None:
    return CLAIM_GROUPS.get(slug) or (BY_SLUG[slug].group if slug in BY_SLUG else None)


def vectors(recognizer: FishRecognizer, photos: list[dict], cache: Path = CACHE) -> np.ndarray:
    """Each photo's vector, cached per encoder and way of reading (the head doesn't change them)."""
    path = cache / f"vectors-{recognizer.encoder.replace('/', '-').replace('@', '-')}-{recognizer.READING}.npz"
    cached = dict(np.load(path)) if path.exists() else {}
    out, fresh = [], 0
    for p in photos:
        key = str(p["gbif_id"])
        if key not in cached:
            with Image.open(cache / p["file"]) as img:
                cached[key] = recognizer.embed(img)
            fresh += 1
        out.append(cached[key])
    if fresh:
        np.savez(path, **cached)
    return np.stack(out)


def evaluate(recognizer: FishRecognizer, photos: list[dict], vecs: np.ndarray, policy: Policy) -> dict:
    r: dict = defaultdict(Counter)
    per_species: dict[str, Counter] = defaultdict(Counter)
    confusions: Counter = Counter()
    for p, v in zip(photos, vecs):
        ident = recognizer.identify_vector(v)
        truth = p["slug"]
        is_guide = truth in BY_SLUG and BY_SLUG[truth].kind == GUIDE
        top_fish = ident.fish(1)[0].slug
        if is_guide:
            r["top1"]["photos"] += 1
            r["top1"]["right"] += top_fish == truth
            r["top1"]["group"] += _group(top_fish) is not None and _group(top_fish) == _group(truth)
            if top_fish != truth:
                confusions[(truth, top_fish)] += 1
        else:
            r["lookalike"]["photos"] += 1
            r["lookalike"]["named"] += top_fish == truth
        for claim in CLAIMS:
            v_ = check_claim(ident, claim, policy)
            if is_guide and claim == truth:
                kind = "true"
                per_species[truth][v_.status] += 1
            else:
                # A fish with no guide is judged by the same groups: a grass
                # carp posted as a common carp is the same kind of fish, as a
                # bass another kind altogether.
                kind = "same_group" if _group(truth) is not None and _group(claim) == _group(truth) else "other_group"
                if not is_guide:
                    kind = "lookalike_" + kind
            r[kind]["claims"] += 1
            r[kind][v_.status] += 1
            r[kind]["accepted"] += v_.accepted
    return {"r": r, "per_species": per_species, "confusions": confusions}


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:.1f}%" if b else "–"


def report(res: dict, model: str, n_photos: int, policy: Policy) -> str:
    r, per = res["r"], res["per_species"]
    t, o, s = r["true"], r["other_group"], r["same_group"]
    lo, ls = r["lookalike_other_group"], r["lookalike_same_group"]
    lines = [
        f"# Fish photo check: measured ({model})",
        "",
        f"{n_photos} photos (research-grade iNaturalist via GBIF, CC0/CC BY, US, 2024 on); policy {policy}.",
        "",
        "| What | Result |",
        "|---|---|",
        f"| Top answer is the right species (guide photos) | {pct(r['top1']['right'], r['top1']['photos'])} of {r['top1']['photos']} |",
        f"| Top answer in the right look-alike group | {pct(r['top1']['group'], r['top1']['photos'])} |",
        f"| True claim accepted | {pct(t['accepted'], t['claims'])} ({pct(t[CONFIRMED], t['claims'])} as the species, {pct(t[GROUP], t['claims'])} as its group) |",
        f"| True claim refused (retake asked) | {pct(t['claims'] - t['accepted'], t['claims'])}: "
        f"no fish seen {pct(t[NO_FISH], t['claims'])}, unsure {pct(t[UNSURE], t['claims'])}, "
        f"read as another guide fish {pct(t[MISMATCH], t['claims'])}, as a fish with no guide {pct(t[OTHER], t['claims'])} |",
        f"| **False claim, another kind of fish, accepted** | **{pct(o['accepted'], o['claims'])}** ({o['accepted']} of {o['claims']}) |",
        f"| False claim, same group, accepted as the group | {pct(s[GROUP], s['claims'])} |",
        f"| False claim, same group, confirmed as the species | {pct(s[CONFIRMED], s['claims'])} |",
        f"| **Fish with no guide, claimed as another kind of fish, accepted** | **{pct(lo['accepted'], lo['claims'])}** ({lo['accepted']} of {lo['claims']}) |",
        f"| Fish with no guide, claimed as a guide species of its group: as the group / as the species | "
        f"{pct(ls[GROUP], ls['claims'])} / {pct(ls[CONFIRMED], ls['claims'])} |",
        f"| Fish with no guide named correctly | {pct(r['lookalike']['named'], r['lookalike']['photos'])} of {r['lookalike']['photos']} |",
        "",
        "## True claims, per species",
        "",
        "| Species | Photos | Confirmed | As group | Refused |",
        "|---|---|---|---|---|",
    ]
    for slug, c in sorted(per.items()):
        n = sum(c.values())
        lines.append(f"| {BY_SLUG[slug].common} | {n} | {pct(c[CONFIRMED], n)} | {pct(c[GROUP], n)} | {pct(n - c[CONFIRMED] - c[GROUP], n)} |")
    lines += ["", "## Commonest mix-ups (truth → top answer)", ""]
    for (a, b), n in res["confusions"].most_common(15):
        lines.append(f"- {BY_SLUG[a].common} → {BY_SLUG.get(b).common if b in BY_SLUG else b}: {n}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model-dir", type=Path, default=Path("models/fish-id"))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--sweep", action="store_true", help="also try other thresholds")
    args = parser.parse_args(argv)

    photos = json.loads((CACHE / "manifest.json").read_text("utf-8"))["photos"]
    recognizer = FishRecognizer(args.model_dir)
    vecs = vectors(recognizer, photos)
    res = evaluate(recognizer, photos, vecs, POLICY)
    text = report(res, recognizer.name, len(photos), POLICY)
    print(text)
    if args.sweep:
        print("confirm group contradict min_fish | true-accepted other-group-accepted same-group-confirmed lookalike-accepted")
        for confirm in (0.35, 0.5, 0.65):
            for group in (0.5, 0.6, 0.75):
                for contradict in (0.3, 0.4):
                    pol = replace(POLICY, confirm=confirm, group=group, contradict=contradict)
                    r = evaluate(recognizer, photos, vecs, pol)["r"]
                    print(
                        f"{confirm:.2f} {group:.2f} {contradict:.2f} {pol.min_fish:.2f} | "
                        f"{pct(r['true']['accepted'], r['true']['claims'])} {pct(r['other_group']['accepted'], r['other_group']['claims'])} "
                        f"{pct(r['same_group'][CONFIRMED], r['same_group']['claims'])} {pct(r['lookalike']['accepted'], r['lookalike']['claims'])}"
                    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
