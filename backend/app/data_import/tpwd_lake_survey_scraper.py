"""Real data ingestion from TPWD Lake Survey Reports for the College
Station - Houston corridor (PRD scope narrowed from statewide to this
region — see docs/adr/0002-tpwd-data-ingestion.md for the full reasoning).

WHAT THIS DOES NOT DO, on purpose
----------------------------------
TPWD's robots.txt (https://tpwd.texas.gov/robots.txt) explicitly disallows
crawling any URL containing a query string ("?", "$" rules under
`User-agent: *`). That rules out the `stock_bywater.php?WB_code=...`
stocking-history endpoint, even though it returns clean, easy-to-parse
HTML. This scraper only ever fetches static, query-string-free report
index pages (".../lake_survey/pwd_rp_t3200_XXXX/"), which are not covered
by that disallow rule. If TPWD's robots.txt ever changes to block these
too, TARGET_WATERBODIES should be re-vetted before running this again —
don't just remove the check.

WHAT THIS DOES
--------------
Each report index page includes a "Fish Community" narrative paragraph
(e.g. "Important sport fishes include Channel Catfish, Blue Catfish,
White Bass, ..."). Rather than attempting to grammatically parse arbitrary
prose (fragile, and a bad idea for data that gets shown to users as fact),
this does *substring matching* against a curated list of species names and
common aliases, and keeps the sentence it matched as the `evidence` field
on WaterbodySpecies — so every extracted fact stays traceable to the exact
source text a human can double check. This is deliberately conservative:
a species mentioned only in passing (e.g. inside a citation) can produce
a false positive, which is exactly why every row is tagged
`confidence="confirmed"` + a source_url + an evidence sentence rather than
silently trusted as ground truth.

Run:
    python -m app.data_import.tpwd_lake_survey_scraper
    python -m app.data_import.tpwd_lake_survey_scraper --dry-run   # fetch + parse only, no DB writes
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.db.session import Base, SessionLocal, engine
from app.models.waterbody import Species, SourceRecord, State, Waterbody, WaterbodySpecies

# Be a polite, identifiable, rate-limited client. TPWD didn't ask for this,
# but "the scraper introduces itself and doesn't hammer a state agency's
# server" is the bar for a data pipeline I'd put my name on.
REQUEST_DELAY_SECONDS = 2.0
REQUEST_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class TargetWaterbody:
    name: str
    county: str
    latitude: float
    longitude: float
    survey_index_url: str  # static path, no query string — see module docstring


# College Station - Houston corridor only (deliberately narrowed scope —
# see docs/adr/0002-tpwd-data-ingestion.md). Coordinates are lake
# centroids, approximate to a few hundred meters — fine for "which lakes
# are near me" radius filtering, not for navigation.
TARGET_WATERBODIES: list[TargetWaterbody] = [
    TargetWaterbody(
        name="Lake Somerville",
        county="Burleson / Lee / Washington",
        latitude=30.3399,
        longitude=-96.5397,
        survey_index_url="https://tpwd.texas.gov/publications/pwdpubs/lake_survey/pwd_rp_t3200_1374/",
    ),
    TargetWaterbody(
        name="Lake Bryan",
        county="Brazos",
        latitude=30.7188,
        longitude=-96.4275,
        survey_index_url="https://tpwd.texas.gov/publications/pwdpubs/lake_survey/pwd_rp_t3200_1257/",
    ),
    TargetWaterbody(
        name="Lake Conroe",
        county="Montgomery",
        latitude=30.3949,
        longitude=-95.6300,
        survey_index_url="https://tpwd.texas.gov/publications/pwdpubs/lake_survey/pwd_rp_t3200_1278/",
    ),
    TargetWaterbody(
        name="Lake Houston",
        county="Harris / Montgomery",
        latitude=29.9394,
        longitude=-95.1672,
        survey_index_url="https://tpwd.texas.gov/publications/pwdpubs/lake_survey/pwd_rp_t3200_1309/",
    ),
    TargetWaterbody(
        name="Lake Livingston",
        county="Polk / San Jacinto / Trinity / Walker",
        latitude=30.7160,
        longitude=-95.0100,
        survey_index_url="https://tpwd.texas.gov/publications/pwdpubs/lake_survey/pwd_rp_t3200_1326/",
    ),
    TargetWaterbody(
        name="Fayette County Reservoir",
        county="Fayette",
        latitude=29.9127,
        longitude=-96.7280,
        survey_index_url="https://tpwd.texas.gov/publications/pwdpubs/lake_survey/pwd_rp_t3200_1292/",
    ),
    TargetWaterbody(
        name="Gibbons Creek Reservoir",
        county="Grimes",
        latitude=30.6270,
        longitude=-96.0400,
        survey_index_url="https://tpwd.texas.gov/publications/pwdpubs/lake_survey/pwd_rp_t3200_1296/",
    ),
]

# Canonical species name -> aliases as they actually appear in TPWD prose.
# This list is intentionally curated by hand rather than "whatever regex
# matches a capitalized noun phrase" — false positives here become false
# facts shown to an angler, which is the one thing PRD §4.2 says never to
# do. Extend this list deliberately, not automatically.
KNOWN_SPECIES: dict[str, list[str]] = {
    "Largemouth Bass": ["largemouth bass", "florida largemouth bass"],
    "Channel Catfish": ["channel catfish"],
    "Blue Catfish": ["blue catfish"],
    "White Bass": ["white bass"],
    "Hybrid Striped Bass": ["hybrid striped bass", "sunshine bass", "palmetto bass"],
    "Striped Bass": ["striped bass"],
    "White Crappie": ["white crappie"],
    "Black Crappie": ["black crappie"],
    "Bluegill": ["bluegill"],
    "Gizzard Shad": ["gizzard shad"],
    "Threadfin Shad": ["threadfin shad"],
    "Spotted Bass": ["spotted bass"],
}

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def fetch_report_html(url: str, user_agent: str) -> str:
    """Fetch one report index page. Raises on HTTP/network failure —
    callers decide whether one bad lake should stop the whole run."""
    if "?" in url or "$" in url:
        raise ValueError(
            f"Refusing to fetch a query-string URL ({url!r}) — disallowed by "
            "TPWD's robots.txt. See module docstring."
        )
    headers = {"User-Agent": user_agent}
    with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def page_text(html: str) -> str:
    """Strip an HTML report page down to plain text for substring matching."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


@dataclass(frozen=True)
class SpeciesMention:
    species_name: str
    evidence_sentence: str


def extract_species_mentions(text: str) -> list[SpeciesMention]:
    """Substring-match KNOWN_SPECIES against page text, sentence by
    sentence, so every hit carries the exact sentence it came from as
    evidence. A species matched by more than one alias in the same
    sentence is only recorded once."""
    sentences = _SENTENCE_SPLIT_RE.split(text)
    seen: set[str] = set()
    mentions: list[SpeciesMention] = []
    for sentence in sentences:
        lowered = sentence.lower()
        for canonical_name, aliases in KNOWN_SPECIES.items():
            if canonical_name in seen:
                continue
            if any(alias in lowered for alias in aliases):
                mentions.append(SpeciesMention(canonical_name, sentence.strip()))
                seen.add(canonical_name)
    return mentions


def upsert_waterbody(db, target: TargetWaterbody, tx_state: State) -> Waterbody:
    existing = db.query(Waterbody).filter_by(name=target.name, state_id=tx_state.id).first()
    if existing:
        return existing
    wb = Waterbody(
        state_id=tx_state.id,
        name=target.name,
        latitude=target.latitude,
        longitude=target.longitude,
        access_summary=(
            f"See TPWD survey report for {target.name} ({target.county} County) "
            "for angler access details."
        ),
        source_url=target.survey_index_url,
        source_updated_at=datetime.now(timezone.utc),
        field_tested=False,
    )
    db.add(wb)
    db.flush()
    return wb


def upsert_species(db, canonical_name: str) -> Species:
    existing = db.query(Species).filter_by(common_name=canonical_name).first()
    if existing:
        return existing
    species = Species(
        common_name=canonical_name,
        scientific_name="",  # not extracted from this source; fill in separately if needed
        difficulty="intermediate",
        profile="Documented in a TPWD lake survey report. Profile pending manual review.",
    )
    db.add(species)
    db.flush()
    return species


def ingest_one_lake(db, target: TargetWaterbody, tx_state: State, user_agent: str) -> int:
    """Returns the number of species links written for this lake."""
    if not target.survey_index_url:
        print(f"  skip {target.name}: no survey_index_url resolved yet")
        return 0

    html = fetch_report_html(target.survey_index_url, user_agent)
    text = page_text(html)
    mentions = extract_species_mentions(text)
    if not mentions:
        print(f"  {target.name}: fetched OK but found 0 known-species mentions — "
              f"check KNOWN_SPECIES coverage or page structure before trusting this as 'no fish'")
        return 0

    waterbody = upsert_waterbody(db, target, tx_state)
    now = datetime.now(timezone.utc)

    source = SourceRecord(
        source_type="tpwd_survey",
        url=target.survey_index_url,
        publisher="Texas Parks and Wildlife Department — Inland Fisheries Division",
        retrieved_at=now,
        valid_until=None,
        checksum=None,
    )
    db.add(source)

    written = 0
    for mention in mentions:
        species = upsert_species(db, mention.species_name)
        link = (
            db.query(WaterbodySpecies)
            .filter_by(waterbody_id=waterbody.id, species_id=species.id)
            .first()
        )
        if link is None:
            link = WaterbodySpecies(waterbody_id=waterbody.id, species_id=species.id)
            db.add(link)
        link.confidence = "confirmed"
        link.evidence = mention.evidence_sentence
        link.source_url = target.survey_index_url
        link.observed_at = now
        written += 1

    print(f"  {target.name}: {written} species mention(s) recorded")
    return written


def run(dry_run: bool = False) -> None:
    settings = get_settings()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        tx_state = db.query(State).filter_by(code="TX").first()
        if tx_state is None:
            tx_state = State(
                name="Texas",
                code="TX",
                official_source_url="https://tpwd.texas.gov/fishboat/fish/recreational/lakes/",
            )
            db.add(tx_state)
            db.flush()

        total_written = 0
        for i, target in enumerate(TARGET_WATERBODIES):
            print(f"[{i + 1}/{len(TARGET_WATERBODIES)}] {target.name}")
            try:
                total_written += ingest_one_lake(db, target, tx_state, settings.tpwd_user_agent)
            except httpx.HTTPError as exc:
                print(f"  FAILED ({exc.__class__.__name__}): {exc} — continuing with next lake")
            except ValueError as exc:
                print(f"  REFUSED: {exc}")

            if i < len(TARGET_WATERBODIES) - 1:
                time.sleep(REQUEST_DELAY_SECONDS)

        if dry_run:
            print(f"Dry run — rolling back {total_written} species link(s), nothing persisted.")
            db.rollback()
        else:
            db.commit()
            print(f"Done — {total_written} species link(s) committed.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and parse everything, print what would be written, but don't commit.",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)
    sys.exit(0)
