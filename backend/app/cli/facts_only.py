"""Make stored agency data "facts + link" only, and prove it.

Before docs/adr/0034, the TPWD import kept, as each species' evidence, the
sentence of TPWD's survey report that named the fish ("Important sport fish
include Largemouth Bass, Channel Catfish, sunfish, and crappie.") or the
lake page's list item, and kept TPWD's own description of where each lake
is. Those are TPWD's words. The importers now write FishEye's own sentences
(tpwd_statewide_import.survey_evidence); this rewrites rows already stored,
on SQLite or PostgreSQL alike (plain ORM updates, no SQL dialect).

    python -m app.cli.facts_only            # rewrite, then check
    python -m app.cli.facts_only --check    # only check

The check compares every stored text a user can see (species evidence,
lake summaries, agency profiles) with the agency pages the importers read
(tpwd_cache/, ga_wrd_cache/, records_cache/): any run of CHECK_WORDS
words found in both is reported. Exit status 1 when anything is found.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data_import.species_names import GENERIC_NAMES, SPECIES, species_list
from app.data_import.tpwd_statewide_import import lake_page_evidence, survey_evidence
from app.models.waterbody import (
    AgencyLakeProfile,
    SpeciesEvidence,
    Waterbody,
    WaterbodySpecies,
)

TPWD = "https://tpwd.texas.gov/"
TPWD_LAKE_PAGES = "/fishboat/fish/recreational/lakes/"
CHECK_WORDS = 8
CACHES = (Path("tpwd_cache"), Path("ga_wrd_cache"), Path("records_cache"))


def rewrite(db: Session) -> dict[str, int]:
    counts = {"tpwd_evidence": 0, "tpwd_locations": 0, "species_lists": 0}
    profiles = {p.waterbody_id: p for p in db.scalars(select(AgencyLakeProfile).where(AgencyLakeProfile.agency == "tpwd"))}
    for link in db.scalars(select(WaterbodySpecies).where(WaterbodySpecies.source_url.startswith(TPWD))):
        name = link.species.common_name
        profile = profiles.get(link.waterbody_id)
        # Only the two kinds of TPWD page the old import quoted. Other TPWD
        # links (water body records) already carry FishEye's own sentence.
        if "/lake_survey/" in link.source_url or "pwdpubs" in link.source_url:
            year = profile.survey_year if profile and profile.survey_report_url == link.source_url else None
            new = survey_evidence(name, year)
        elif TPWD_LAKE_PAGES in link.source_url:
            new = lake_page_evidence(name)
        else:
            continue
        if link.evidence != new:
            link.evidence = new
            counts["tpwd_evidence"] += 1
    for p in profiles.values():
        if p.location is not None:
            p.location = None
            counts["tpwd_locations"] += 1
    for p in db.scalars(select(AgencyLakeProfile)):
        ours = species_list(list(p.predominant_species or []))
        if ours != list(p.predominant_species or []):
            p.predominant_species = ours
            counts["species_lists"] += 1
    db.flush()
    return counts


# --------------------------------------------------------------------------
# Check
# --------------------------------------------------------------------------

_WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


_URL = re.compile(r"https?://\S+")


def _words(text: str) -> list[str]:
    """Lower-case words; links are not prose and are dropped first."""
    return _WORD.findall(_URL.sub(" ", text).lower())


def _shingles(words: list[str]) -> Iterator[tuple[str, ...]]:
    for i in range(len(words) - CHECK_WORDS + 1):
        yield tuple(words[i : i + CHECK_WORDS])


def _source_texts(caches: tuple[Path, ...]) -> Iterator[str]:
    for cache in caches:
        if not cache.exists():
            continue
        for path in cache.rglob("*"):
            if path.suffix == ".html":
                raw = path.read_text(encoding="utf-8", errors="ignore")
                raw = re.sub(r"<(script|style)\b.*?</\1>", " ", raw, flags=re.S | re.I)
                yield html.unescape(re.sub(r"<[^>]+>", " ", raw))
            elif path.suffix == ".json" and path.stat().st_size < 50_000_000:
                def strings(v: object) -> Iterator[str]:
                    if isinstance(v, str):
                        yield v
                    elif isinstance(v, dict):
                        for x in v.values():
                            yield from strings(x)
                    elif isinstance(v, list):
                        for x in v:
                            yield from strings(x)
                try:
                    yield " \n ".join(strings(json.loads(path.read_text(encoding="utf-8"))))
                except ValueError:
                    continue


def _stored_texts(db: Session) -> Iterator[tuple[str, str]]:
    for link in db.scalars(select(WaterbodySpecies)):
        yield f"waterbody_species {link.waterbody_id}/{link.species_id}", link.evidence
    for e in db.scalars(select(SpeciesEvidence)):
        yield f"species_evidence {e.id}", e.evidence
    for p in db.scalars(select(AgencyLakeProfile)):
        yield f"agency_lake_profiles {p.id} location", p.location or ""
        items = p.predominant_species or []
        # A list made only of fish names is a list of facts, whatever order
        # another list happens to share; anything else in it is checked.
        if not all(i in SPECIES or i in GENERIC_NAMES for i in items):
            yield f"agency_lake_profiles {p.id} species", " ; ".join(items)
    for wb in db.scalars(select(Waterbody).where(Waterbody.data_tier == "verified")):
        yield f"waterbodies {wb.id} access_summary", wb.access_summary or ""


def check(db: Session, caches: tuple[Path, ...] = CACHES) -> list[tuple[str, str]]:
    """(row, copied words) for every stored text sharing a CHECK_WORDS-word
    run with an agency page."""
    source: set[tuple[str, ...]] = set()
    for text in _source_texts(caches):
        source.update(_shingles(_words(text)))
    found = []
    for where, text in _stored_texts(db):
        for sh in _shingles(_words(text)):
            if sh in source:
                found.append((where, " ".join(sh)))
                break
    return found


def main(argv: list[str] | None = None) -> int:
    from app.db.session import SessionLocal, engine
    from app.db.upgrades import prepare_database

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="only check, change nothing")
    ap.add_argument("--caches", type=Path, default=Path("."),
                    help="folder holding tpwd_cache/, ga_wrd_cache/ and records_cache/ (default: here)")
    args = ap.parse_args(argv)
    caches = tuple(args.caches / c for c in CACHES)
    if not any(c.exists() for c in caches):
        print(f"No agency caches under {args.caches}: nothing to check against.", file=sys.stderr)
        return 2
    prepare_database(engine)
    with SessionLocal() as db:
        if not args.check:
            counts = rewrite(db)
            db.commit()
            print(f"rewrote {counts['tpwd_evidence']} TPWD evidence sentences; "
                  f"removed {counts['tpwd_locations']} TPWD location descriptions; "
                  f"rewrote {counts['species_lists']} predominant-species lists as FishEye's own")
        found = check(db, caches)
    if found:
        print(f"{len(found)} stored texts share {CHECK_WORDS}+ words with an agency page:")
        for where, words in found[:50]:
            print(f"  {where}: “{words}”")
        return 1
    print(f"check: no stored text shares {CHECK_WORDS} consecutive words with the cached TPWD, "
          "Georgia WRD or record pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
