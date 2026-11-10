"""Photos to measure the fish recognizer against (app/services/fish_id.py).

    python -m app.cli.fish_id_photos                 # the test set, fishid_cache/
    python -m app.cli.fish_id_photos --train         # the training set, fishid_cache/train/

Research-grade iNaturalist observations, through GBIF (the data-sourcing
skill: iNaturalist only through GBIF, licence-filtered), photo licence CC0
or CC BY 4.0 only, observed in the US from 2024 on: newer than the photos
BioCLIP was trained on (its TreeOfLife-10M set was assembled in 2023), so
the measurement is not of photos the model has already seen.

One photo per observation (an observation's photos are near-duplicates),
iNaturalist's "medium" size (500 px, all the recognizer looks at is 224 px),
one request at a time, a second apart, with FishEye's User-Agent. Each
photo's observation, licence and creator go in manifest.json: the photos
are for measuring locally and are never shipped or shown.

The training set (--train) is a different set of observations, from 2015
to 2023: the recognizer's classifier head is fitted on it
(app/cli/fish_id_train.py), and measured only on the test set. Shipping a
head fitted on CC BY photos is shipping an adaptation of them, so their
creators are credited in the model's TRAINING_CREDITS.json.

Besides the guide species, look-alikes FishEye has no guide for (walleye,
pike, gar…): the recognizer must say "not one of ours", not force them
into the nearest guide species.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from app.data_import.provenance import USER_AGENT
from app.knowledge.species_guides import GUIDES
from app.services.fish_id_classes import BY_SLUG, CLASSES, OTHER_FISH, SAME_FISH

CACHE = Path("fishid_cache")
GBIF = "https://api.gbif.org/v1"
INATURALIST_DATASET = "50c9509d-22c7-4a22-a47d-8c48425ef4a7"  # iNaturalist research-grade
LICENCES = {"http://creativecommons.org/licenses/by/4.0/": "CC BY 4.0", "http://creativecommons.org/publicdomain/zero/1.0/": "CC0 1.0"}
PAUSE_S = 1.0

# Freshwater fish an angler in the US may well catch that have no guide:
# the recognizer's "other fish" classes.
# A steelhead has no taxon of its own (it is a rainbow trout, SAME_FISH):
# a search by its scientific name would bring rainbow trout, so its photos
# come from fish_id_commons.py instead.
LOOKALIKES = {c.slug: c.scientific for c in CLASSES if c.kind == OTHER_FISH and c.slug not in SAME_FISH}


def targets() -> dict[str, str]:
    """slug → scientific name: the guide species, then the look-alikes."""
    out = {
        g.slug: g.scientific_name
        for g in GUIDES
        if g.slug in BY_SLUG and "×" not in g.scientific_name and " x " not in g.scientific_name
    }
    out.update(LOOKALIKES)
    return out


def pick_photos(results: list[dict[str, Any]], want: int, seen: set[str]) -> list[dict[str, Any]]:
    """The first openly licensed photo of each observation, in medium size."""
    picked = []
    for occ in results:
        if len(picked) >= want:
            break
        obs = occ.get("occurrenceID") or str(occ.get("key"))
        if obs in seen:
            continue
        for m in occ.get("media") or []:
            url, licence = m.get("identifier") or "", LICENCES.get(m.get("license") or "")
            if m.get("type") == "StillImage" and licence and "/original." in url:
                seen.add(obs)
                picked.append(
                    {
                        "gbif_id": occ["key"],
                        "observation": obs,
                        "url": url.replace("/original.", "/medium."),
                        "licence": licence,
                        "creator": m.get("creator") or m.get("rightsHolder") or "",
                    }
                )
                break
    return picked


def fetch(per_species: int, lookalikes: int, cache: Path = CACHE, years: str = "2024,2026", scan: int = 900) -> dict[str, Any]:
    import httpx

    client = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60, follow_redirects=True)

    def get(url: str, **params: Any) -> httpx.Response:
        time.sleep(PAUSE_S)
        for attempt in range(4):
            resp = client.get(url, params=params or None)
            if resp.status_code not in (429, 500, 502, 503, 504):
                resp.raise_for_status()
                return resp
            time.sleep(10 * (attempt + 1))
        resp.raise_for_status()
        return resp

    manifest_path = cache / "manifest.json"
    manifest: dict[str, Any] = json.loads(manifest_path.read_text("utf-8")) if manifest_path.exists() else {"photos": []}
    have = {(p["slug"], p["gbif_id"]) for p in manifest["photos"]}
    for slug, name in targets().items():
        want = lookalikes if slug in LOOKALIKES else per_species
        mine = [p for p in manifest["photos"] if p["slug"] == slug]
        if len(mine) >= want:
            continue
        key = get(f"{GBIF}/species/match", name=name).json().get("usageKey")
        if key is None:
            print(f"  {slug}: GBIF has no taxon for {name}; skipped", file=sys.stderr)
            continue
        seen = {p["observation"] for p in mine}
        picked: list[dict[str, Any]] = []
        # Only some photos are CC0 or CC BY (iNaturalist's default is CC BY-NC),
        # so a fish with few photos needs a deeper scan (--scan).
        for offset in range(0, scan, 300):
            page = get(
                f"{GBIF}/occurrence/search",
                taxonKey=key, mediaType="StillImage", datasetKey=INATURALIST_DATASET,
                license=["CC0_1_0", "CC_BY_4_0"], year=years, country="US", limit=300, offset=offset,
            ).json()
            picked += pick_photos(page["results"], want - len(mine) - len(picked), seen)
            if len(mine) + len(picked) >= want or page.get("endOfRecords"):
                break
        folder = cache / "photos" / slug
        folder.mkdir(parents=True, exist_ok=True)
        for p in picked:
            if (slug, p["gbif_id"]) in have:
                continue
            target = folder / f"{p['gbif_id']}.jpg"
            try:
                target.write_bytes(get(p["url"]).content)
            except Exception as exc:  # noqa: BLE001 - one bad photo must not stop the set
                print(f"  {slug}: {p['url']}: {exc}", file=sys.stderr)
                continue
            manifest["photos"].append({**p, "slug": slug, "file": str(target.relative_to(cache)).replace("\\", "/")})
        manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        print(f"  {slug}: {len([p for p in manifest['photos'] if p['slug'] == slug])} photos")
    return manifest


def fetch_steelhead(cache: Path = CACHE / "train") -> int:
    """Rainbow trout observations whose text calls them steelhead (GBIF's
    full-text `q`), every year, CC0 or CC BY: a steelhead has no taxon of
    its own. Into the training set only, for a person to look over before
    fitting (fish_id_commons.py says why: what's called steelhead often
    isn't a photo of one)."""
    import httpx

    client = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60, follow_redirects=True)
    key = client.get(f"{GBIF}/species/match", params={"name": "Oncorhynchus mykiss"}).json()["usageKey"]
    time.sleep(PAUSE_S)
    page = client.get(
        f"{GBIF}/occurrence/search",
        params={"taxonKey": key, "q": "steelhead", "mediaType": "StillImage", "datasetKey": INATURALIST_DATASET,
                "license": ["CC0_1_0", "CC_BY_4_0"], "limit": 300},
    ).json()
    manifest_path = cache / "manifest.json"
    manifest = json.loads(manifest_path.read_text("utf-8"))
    have = {str(p["gbif_id"]) for p in manifest["photos"]}
    folder = cache / "photos" / "steelhead"
    folder.mkdir(parents=True, exist_ok=True)
    added = 0
    for photo in pick_photos(page["results"], 300, set()):
        if str(photo["gbif_id"]) in have:
            continue
        time.sleep(PAUSE_S)
        target = folder / f"{photo['gbif_id']}.jpg"
        try:
            target.write_bytes(client.get(photo["url"]).content)
        except Exception as exc:  # noqa: BLE001 - one bad photo must not stop the set
            print(f"  steelhead: {photo['url']}: {exc}", file=sys.stderr)
            continue
        manifest["photos"].append({**photo, "slug": "steelhead", "file": str(target.relative_to(cache)).replace("\\", "/")})
        added += 1
    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"steelhead: {added} iNaturalist photos added to {cache}")
    return added


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--per-species", type=int, default=50)
    parser.add_argument("--lookalikes", type=int, default=20, help="photos per look-alike species")
    parser.add_argument("--train", action="store_true", help="the training set: 2015-2023, fishid_cache/train/")
    parser.add_argument("--scan", type=int, default=900, help="observations to look through per fish for open photos")
    parser.add_argument("--steelhead", action="store_true", help="only: rainbow trout observations called steelhead, into training")
    args = parser.parse_args(argv)
    if args.steelhead:
        fetch_steelhead()
        return 0
    cache = CACHE / "train" if args.train else CACHE
    manifest = fetch(args.per_species, args.lookalikes, cache, "2015,2023" if args.train else "2024,2026", args.scan)
    print(f"{len(manifest['photos'])} photos in {cache / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
