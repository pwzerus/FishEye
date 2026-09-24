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

WHAT ABOUT ACCESS POINTS
------------------------
The species-mentions pass above is the only thing done as a live,
automated scrape. Public access points are NOT scraped-and-parsed at run
time, even though TPWD publishes a per-lake `access.phtml` page for
exactly this purpose. Those pages give only driving directions ("From the
Lake Conroe bridge on FM 1375 travel west approximately 4 miles, turn
right on Stubblefield Lake Road...") with no coordinates, and turning
open-ended directions prose into structured facilities + lat/lng is a
fundamentally less reliable kind of extraction than the curated
substring-match above — a wrong guess here doesn't just miss a fact, it
plots a pin in the wrong place and tells an angler it's confirmed public
access (exactly what PRD §12 exists to prevent).

Instead, each lake's `access_points` below were identified from its own
TPWD access page and then geocoded against an independent source (a
park's own address, a government GIS boat-ramp dataset, or a facility
listing service) by hand, once, during development — the same character
of work as `seed_tx_lakes.py`'s three Day-1 lakes, just done later. If
TPWD changes access for a lake (as it did for Gibbons Creek Reservoir,
closed to the public since 12/25/21 per its own access page), this list
needs a human to revisit it — that's `public_access_status` below, not
something the scraper infers on its own.

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
from app.knowledge.species_guides import get_guide
from app.models.waterbody import AccessPoint, Species, SourceRecord, State, Waterbody, WaterbodySpecies

# Be a polite, identifiable, rate-limited client. TPWD didn't ask for this,
# but "the scraper introduces itself and doesn't hammer a state agency's
# server" is the bar for a data pipeline I'd put my name on.
REQUEST_DELAY_SECONDS = 2.0
REQUEST_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class NamedAccessPoint:
    """One hand-verified, geocoded public access point — see the module
    docstring section "WHAT ABOUT ACCESS POINTS" for why this is curated
    data, not a live scrape+geocode result."""

    name: str
    latitude: float
    longitude: float
    access_type: str  # bank, pier, boat_ramp, park
    parking: bool = True


@dataclass(frozen=True)
class TargetWaterbody:
    name: str
    county: str
    latitude: float
    longitude: float
    survey_index_url: str  # static path, no query string — see module docstring
    # TPWD's own per-lake access page — kept as a citation even when it's
    # not machine-parsed (see module docstring).
    access_page_url: str | None = None
    access_points: tuple[NamedAccessPoint, ...] = ()
    # "open" | "closed" — see Waterbody.public_access_status.
    public_access_status: str = "open"


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
        access_page_url="https://tpwd.texas.gov/fishboat/fish/recreational/lakes/somerville/access.phtml",
        access_points=(
            # TPWD names this "State Park Nails Creek Unit" — coordinates
            # from the unit's own boat-ramp facility (Natural Atlas).
            NamedAccessPoint("Nails Creek Unit Boat Ramp", 30.295163, -96.664021, "boat_ramp"),
            # TPWD names this "Welch Park" — coordinates from the park's
            # own boat-ramp facility (Natural Atlas).
            NamedAccessPoint("Welch Park Boat Ramp", 30.338507, -96.551357, "boat_ramp"),
        ),
    ),
    TargetWaterbody(
        name="Lake Bryan",
        county="Brazos",
        latitude=30.7188,
        longitude=-96.4275,
        survey_index_url="https://tpwd.texas.gov/publications/pwdpubs/lake_survey/pwd_rp_t3200_1257/",
        access_page_url="https://tpwd.texas.gov/fishboat/fish/recreational/lakes/bryan/access.phtml",
        access_points=(
            # TPWD's access page names only "City Park & Ramp" with no
            # address. Destination Bryan's own visitor listing identifies
            # it as the 8200 Sandy Point Rd park entrance — "the only
            # public boat ramp in Brazos County" — geocoded via Campendium's
            # campground listing at that address.
            NamedAccessPoint("Lake Bryan Park & Boat Ramp", 30.708623, -96.464741, "boat_ramp"),
        ),
    ),
    TargetWaterbody(
        name="Lake Conroe",
        county="Montgomery",
        latitude=30.3949,
        longitude=-95.6300,
        survey_index_url="https://tpwd.texas.gov/publications/pwdpubs/lake_survey/pwd_rp_t3200_1278/",
        access_page_url="https://tpwd.texas.gov/fishboat/fish/recreational/lakes/conroe/access.phtml",
        access_points=(
            # National Forest Service ramp named directly on TPWD's page;
            # coordinates cross-checked between Natural Atlas and Boat
            # Ramp Finder (they agree to ~30m).
            NamedAccessPoint("Cagle Recreation Area", 30.518858, -95.591545, "boat_ramp"),
            # Named on TPWD's page; address (13988 Calvary Rd, Willis, TX)
            # geocoded via Campendium's RV-park listing at that address.
            NamedAccessPoint("Stow-A-Way Marina", 30.473411, -95.567240, "boat_ramp"),
        ),
    ),
    TargetWaterbody(
        name="Lake Houston",
        county="Harris / Montgomery",
        latitude=29.9394,
        longitude=-95.1672,
        survey_index_url="https://tpwd.texas.gov/publications/pwdpubs/lake_survey/pwd_rp_t3200_1309/",
        access_page_url="https://tpwd.texas.gov/fishboat/fish/recreational/lakes/houston/access.phtml",
        access_points=(
            # TPWD names this "Deussen Park" — coordinates from the park's
            # own boat-ramp facility (Natural Atlas).
            NamedAccessPoint("Alexander Deussen Park", 29.916873, -95.146803, "boat_ramp"),
        ),
    ),
    TargetWaterbody(
        name="Lake Livingston",
        county="Polk / San Jacinto / Trinity / Walker",
        latitude=30.7160,
        longitude=-95.0100,
        survey_index_url="https://tpwd.texas.gov/publications/pwdpubs/lake_survey/pwd_rp_t3200_1326/",
        access_page_url="https://tpwd.texas.gov/fishboat/fish/recreational/lakes/livingston/access.phtml",
        access_points=(
            # TPWD's page lists several free ramps plus this fee marina;
            # the marina is chosen here because it's the one with an
            # independently verifiable coordinate (fishing.org).
            NamedAccessPoint(
                "Lake Livingston State Park Marina", 30.664731, -95.002948, "boat_ramp"
            ),
        ),
    ),
    TargetWaterbody(
        name="Fayette County Reservoir",
        county="Fayette",
        latitude=29.9127,
        longitude=-96.7280,
        survey_index_url="https://tpwd.texas.gov/publications/pwdpubs/lake_survey/pwd_rp_t3200_1292/",
        access_page_url="https://tpwd.texas.gov/fishboat/fish/recreational/lakes/fayette/access.phtml",
        access_points=(
            # TPWD names this park directly; coordinates from Boat Ramp
            # Finder's own listing for this facility.
            NamedAccessPoint("Oak Thicket Park", 29.947383, -96.727050, "boat_ramp"),
        ),
    ),
    TargetWaterbody(
        name="Gibbons Creek Reservoir",
        county="Grimes",
        latitude=30.6270,
        longitude=-96.0400,
        survey_index_url="https://tpwd.texas.gov/publications/pwdpubs/lake_survey/pwd_rp_t3200_1296/",
        access_page_url="https://tpwd.texas.gov/fishboat/fish/recreational/lakes/gibbonscreek/access.phtml",
        # TPWD's own access page states: "Gibbons Creek Reservoir is
        # closed to the public as of 12/25/21." No AccessPoint rows are
        # created for a closed lake, however plausible-looking a named
        # facility (its page still names "TMPA Park") might seem — PRD
        # §12 says never present unconfirmed/closed access as public.
        access_points=(),
        public_access_status="closed",
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
    """Create-or-update, not create-only: a re-run must be able to pick up
    a corrected access_summary/public_access_status (e.g. TPWD closing a
    lake) without requiring the DB to be wiped first. field_tested is
    intentionally left untouched on an update — it's a manual QA flag, not
    something this scraper should ever flip back to False."""
    wb = db.query(Waterbody).filter_by(name=target.name, state_id=tx_state.id).first()
    if wb is None:
        wb = Waterbody(state_id=tx_state.id, name=target.name, field_tested=False)
        db.add(wb)
    elif wb.data_tier != "verified":
        # A same-named row from the statewide OpenStreetMap layer
        # (osm_waterbody_import.py). TPWD is the better source, so the row
        # is promoted in place — keeping its osm_ref, so the next OSM
        # import recognises it as verified and leaves it alone — and its
        # OSM-reported entrances are dropped: verified lakes show only
        # officially sourced access.
        wb.data_tier = "verified"
        wb.access_points = [
            ap for ap in wb.access_points if ap.public_status != "osm_reported"
        ]

    if target.public_access_status == "closed":
        access_summary = (
            f"{target.name} is currently closed to public access, per TPWD's own "
            f"access page ({target.access_page_url}). The species information above "
            "is still from TPWD's lake survey report and may predate the closure."
        )
    else:
        access_summary = (
            f"See TPWD survey report for {target.name} ({target.county} County) "
            "for angler access details."
        )

    wb.latitude = target.latitude
    wb.longitude = target.longitude
    wb.access_summary = access_summary
    wb.source_url = target.survey_index_url
    wb.source_updated_at = datetime.now(timezone.utc)
    wb.public_access_status = target.public_access_status
    db.flush()
    return wb


def upsert_access_points(db, waterbody: Waterbody, target: TargetWaterbody, now: datetime) -> int:
    """Create-or-update the hand-verified AccessPoint rows for this lake
    (see the module docstring's "WHAT ABOUT ACCESS POINTS" section for why
    these are curated data, not scraped-and-geocoded at run time). Returns
    the number of access points written."""
    if target.public_access_status == "closed":
        if target.access_points:
            print(
                f"  WARNING: {target.name} is marked closed but has "
                f"{len(target.access_points)} access_points configured — skipping "
                "them (PRD §12: never present closed access as public)."
            )
        return 0

    written = 0
    for point in target.access_points:
        existing = (
            db.query(AccessPoint)
            .filter_by(waterbody_id=waterbody.id, name=point.name)
            .first()
        )
        if existing is None:
            existing = AccessPoint(waterbody_id=waterbody.id, name=point.name)
            db.add(existing)
        existing.latitude = point.latitude
        existing.longitude = point.longitude
        existing.access_type = point.access_type
        existing.public_status = "confirmed_public"
        existing.parking = point.parking
        # Flush immediately (autoflush is off — see app/db/session.py) so a
        # second point's lookup, or a second call to this function within
        # the same session, sees rows this loop already wrote instead of
        # creating a duplicate.
        db.flush()
        written += 1

    if target.access_page_url:
        already_cited = (
            db.query(SourceRecord)
            .filter_by(source_type="tpwd_access_page", url=target.access_page_url)
            .first()
        )
        if already_cited is None:
            db.add(
                SourceRecord(
                    source_type="tpwd_access_page",
                    url=target.access_page_url,
                    publisher="Texas Parks and Wildlife Department",
                    retrieved_at=now,
                    valid_until=None,
                    checksum=None,
                )
            )

    return written


PLACEHOLDER_PROFILE = "Documented in a TPWD lake survey report. Profile pending manual review."


def upsert_species(db, canonical_name: str) -> Species:
    """Scientific name, difficulty and profile come from the reviewed species
    guides (app/knowledge/species_guides.py), not from the survey page.
    Rows created before the guides existed still carry placeholders; those are
    filled in here, but a value someone set by hand is never overwritten."""
    guide = get_guide(canonical_name)
    species = db.query(Species).filter_by(common_name=canonical_name).first()
    if species is None:
        species = Species(
            common_name=canonical_name,
            scientific_name="",
            difficulty="intermediate",
            profile=PLACEHOLDER_PROFILE,
        )
        db.add(species)
    if guide is not None:
        if not species.scientific_name:
            species.scientific_name = guide.scientific_name
        if species.profile == PLACEHOLDER_PROFILE:
            species.profile = guide.summary
            # The "intermediate" placeholder was never a judgement; replace it
            # alongside the placeholder profile. Forage fish have no rating.
            species.difficulty = guide.difficulty or "n/a"
    db.flush()
    return species


@dataclass(frozen=True)
class LakeResult:
    """Outcome for one lake, in a form an API layer can report without
    scraping stdout — this is what makes the manual-refresh endpoint
    possible without duplicating the ingest logic."""

    name: str
    status: str  # "written" | "skipped_no_url" | "no_mentions" | "failed" | "refused"
    species_written: int = 0
    access_points_written: int = 0
    detail: str = ""


@dataclass(frozen=True)
class IngestSummary:
    lake_results: list[LakeResult]
    total_written: int
    total_access_points_written: int
    dry_run: bool


def ingest_one_lake(db, target: TargetWaterbody, tx_state: State, user_agent: str) -> LakeResult:
    if not target.survey_index_url:
        print(f"  skip {target.name}: no survey_index_url resolved yet")
        return LakeResult(target.name, "skipped_no_url", detail="no survey_index_url resolved yet")

    html = fetch_report_html(target.survey_index_url, user_agent)
    text = page_text(html)
    mentions = extract_species_mentions(text)

    # Waterbody + access-point upserts happen regardless of whether the
    # species-mentions pass finds anything — they're independent facts
    # about the lake (this is also what fixed the real bug where all 7
    # TPWD lakes had zero AccessPoint rows: they used to only get created
    # as a side effect of a non-empty mentions list).
    waterbody = upsert_waterbody(db, target, tx_state)
    now = datetime.now(timezone.utc)
    access_written = upsert_access_points(db, waterbody, target, now)

    if not mentions:
        detail = (
            "fetched OK but found 0 known-species mentions — check KNOWN_SPECIES "
            "coverage or page structure before trusting this as 'no fish'"
        )
        print(f"  {target.name}: {detail}")
        return LakeResult(
            target.name, "no_mentions", access_points_written=access_written, detail=detail
        )

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

    print(
        f"  {target.name}: {written} species mention(s), "
        f"{access_written} access point(s) recorded"
    )
    return LakeResult(
        target.name, "written", species_written=written, access_points_written=access_written
    )


def run(dry_run: bool = False, delay_seconds: float = REQUEST_DELAY_SECONDS) -> IngestSummary:
    """Run the full ingest. Returns an IngestSummary rather than just
    printing, so callers other than the CLI (e.g. the admin refresh API
    endpoint) can report structured results without re-implementing this
    loop. `delay_seconds` is overridable (tests pass 0) — production
    callers should leave it at the default polite delay."""
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

        lake_results: list[LakeResult] = []
        for i, target in enumerate(TARGET_WATERBODIES):
            print(f"[{i + 1}/{len(TARGET_WATERBODIES)}] {target.name}")
            try:
                lake_results.append(ingest_one_lake(db, target, tx_state, settings.tpwd_user_agent))
            except httpx.HTTPError as exc:
                detail = f"{exc.__class__.__name__}: {exc}"
                print(f"  FAILED ({detail}) — continuing with next lake")
                lake_results.append(LakeResult(target.name, "failed", detail=detail))
            except ValueError as exc:
                print(f"  REFUSED: {exc}")
                lake_results.append(LakeResult(target.name, "refused", detail=str(exc)))

            if i < len(TARGET_WATERBODIES) - 1:
                time.sleep(delay_seconds)

        total_written = sum(r.species_written for r in lake_results)
        total_access_points_written = sum(r.access_points_written for r in lake_results)

        if dry_run:
            print(
                f"Dry run — rolling back {total_written} species link(s) and "
                f"{total_access_points_written} access point(s), nothing persisted."
            )
            db.rollback()
        else:
            db.commit()
            print(
                f"Done — {total_written} species link(s) and "
                f"{total_access_points_written} access point(s) committed."
            )

        return IngestSummary(
            lake_results=lake_results,
            total_written=total_written,
            total_access_points_written=total_access_points_written,
            dry_run=dry_run,
        )
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
