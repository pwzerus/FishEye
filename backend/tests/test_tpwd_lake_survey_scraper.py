"""Tests for the TPWD scraper's parsing logic. Deliberately network-free —
see the scraper's module docstring for why real HTTP calls don't belong in
a test suite that runs on every commit. Uses a real (saved) excerpt of the
Lake Somerville survey report page as a fixture so the parsing logic is
tested against actual TPWD prose, not an idealized sentence.
"""
from datetime import datetime, timezone

from app.data_import.tpwd_lake_survey_scraper import (
    KNOWN_SPECIES,
    NamedAccessPoint,
    TargetWaterbody,
    extract_species_mentions,
    fetch_report_html,
    ingest_one_lake,
    page_text,
    upsert_access_points,
    upsert_waterbody,
)
from app.models.waterbody import AccessPoint, State, Waterbody

# Verbatim excerpt from the "Management History" section of the Lake
# Somerville 2020 Fisheries Management Survey Report (retrieved 2026-09,
# https://tpwd.texas.gov/publications/pwdpubs/lake_survey/pwd_rp_t3200_1374/).
SOMERVILLE_EXCERPT = (
    "Management History: Important sport fishes include Channel Catfish, "
    "Blue Catfish, White Bass, Hybrid Striped Bass, Largemouth Bass, White "
    "Crappie and Black Crappie. Recent stockings include Florida Largemouth "
    "Bass and Hybrid Striped Bass. Hydrilla was observed in small quantities "
    "in 2020 but did not negatively impact recreational access."
)

SOMERVILLE_HTML = f"""
<html>
  <head><style>.hidden {{ display: none; }}</style></head>
  <body>
    <nav>Skip to content</nav>
    <header>Texas Parks and Wildlife</header>
    <main>
      <h1>Lake Somerville Survey Report</h1>
      <p>{SOMERVILLE_EXCERPT}</p>
    </main>
    <footer>Contact TPWD</footer>
    <script>console.log("tracking pixel junk that must not leak into text")</script>
  </body>
</html>
"""


def test_page_text_strips_script_style_nav_and_footer():
    text = page_text(SOMERVILLE_HTML)
    assert "tracking pixel junk" not in text
    assert "Skip to content" not in text
    assert "Contact TPWD" not in text
    assert "Important sport fishes" in text


def test_extract_species_mentions_finds_known_species_with_evidence():
    text = page_text(SOMERVILLE_HTML)
    mentions = extract_species_mentions(text)
    names = {m.species_name for m in mentions}

    assert "Channel Catfish" in names
    assert "Blue Catfish" in names
    assert "White Bass" in names
    assert "Hybrid Striped Bass" in names
    assert "Largemouth Bass" in names
    assert "White Crappie" in names
    assert "Black Crappie" in names

    # Every mention carries the sentence it came from, not just the name —
    # this is what makes the extracted fact independently checkable.
    catfish_mention = next(m for m in mentions if m.species_name == "Channel Catfish")
    assert "Important sport fishes include" in catfish_mention.evidence_sentence


def test_extract_species_mentions_deduplicates_across_sentences():
    # "Hybrid Striped Bass" appears in both the first and second sentence —
    # should only be recorded once, keyed to its first sentence.
    text = page_text(SOMERVILLE_HTML)
    mentions = extract_species_mentions(text)
    hybrid_mentions = [m for m in mentions if m.species_name == "Hybrid Striped Bass"]
    assert len(hybrid_mentions) == 1


def test_extract_species_mentions_ignores_species_not_present():
    text = "This lake has excellent Rainbow Trout fishing in winter stockings."
    mentions = extract_species_mentions(text)
    assert mentions == []


def test_extract_species_mentions_handles_empty_text():
    assert extract_species_mentions("") == []


def test_known_species_aliases_are_lowercase():
    # extract_species_mentions lowercases the sentence before matching —
    # if an alias isn't already lowercase it can never match, silently.
    for canonical_name, aliases in KNOWN_SPECIES.items():
        for alias in aliases:
            assert alias == alias.lower(), (
                f"alias {alias!r} for {canonical_name!r} must be lowercase "
                "or it will never match"
            )


def test_fetch_report_html_refuses_query_string_urls():
    import pytest

    with pytest.raises(ValueError, match="robots.txt"):
        fetch_report_html(
            "https://tpwd.texas.gov/fishboat/fish/action/stock_bywater.php?WB_code=0680",
            user_agent="test-agent",
        )


# ---------------------------------------------------------------------------
# Waterbody / access-point upserts — this is the fix for the real bug where
# all 7 TPWD-scraped lakes had zero AccessPoint rows at all (recommendations
# silently returned empty for every one of them), plus the Gibbons Creek
# public-closure handling per PRD §12.
# ---------------------------------------------------------------------------


def _tx_state(db_session) -> State:
    tx = State(name="Texas", code="TX", official_source_url="https://tpwd.texas.gov")
    db_session.add(tx)
    db_session.flush()
    return tx


def _target(**overrides) -> TargetWaterbody:
    defaults = dict(
        name="Test Lake",
        county="Test County",
        latitude=30.0,
        longitude=-96.0,
        survey_index_url="https://tpwd.texas.gov/publications/pwdpubs/lake_survey/pwd_rp_t3200_0000/",
        access_page_url="https://tpwd.texas.gov/fishboat/fish/recreational/lakes/testlake/access.phtml",
    )
    defaults.update(overrides)
    return TargetWaterbody(**defaults)


def test_upsert_waterbody_creates_open_lake_by_default(db_session):
    tx = _tx_state(db_session)
    wb = upsert_waterbody(db_session, _target(), tx)
    assert wb.public_access_status == "open"
    assert "See TPWD survey report" in wb.access_summary


def test_upsert_waterbody_marks_closed_lake_and_explains_why(db_session):
    tx = _tx_state(db_session)
    wb = upsert_waterbody(db_session, _target(public_access_status="closed"), tx)
    assert wb.public_access_status == "closed"
    assert "closed to public access" in wb.access_summary
    assert wb.access_summary.count("access.phtml") == 1  # cites the source page


def test_upsert_waterbody_is_idempotent_and_updates_existing_row(db_session):
    tx = _tx_state(db_session)
    target = _target()
    wb1 = upsert_waterbody(db_session, target, tx)
    db_session.flush()
    wb2 = upsert_waterbody(db_session, _target(latitude=31.0), tx)
    assert wb1.id == wb2.id  # same row, not a duplicate
    assert wb2.latitude == 31.0  # picked up the corrected value on re-run


def test_upsert_waterbody_never_resets_field_tested_to_false(db_session):
    tx = _tx_state(db_session)
    wb = upsert_waterbody(db_session, _target(), tx)
    wb.field_tested = True  # simulate a manual QA pass
    db_session.flush()
    upsert_waterbody(db_session, _target(), tx)  # re-run
    assert wb.field_tested is True


def test_upsert_access_points_writes_confirmed_public_points(db_session):
    tx = _tx_state(db_session)
    target = _target(
        access_points=(
            NamedAccessPoint("Test Park Boat Ramp", 30.01, -96.01, "boat_ramp"),
        )
    )
    wb = upsert_waterbody(db_session, target, tx)
    written = upsert_access_points(db_session, wb, target, datetime.now(timezone.utc))
    db_session.flush()

    assert written == 1
    points = db_session.query(AccessPoint).filter_by(waterbody_id=wb.id).all()
    assert len(points) == 1
    assert points[0].name == "Test Park Boat Ramp"
    assert points[0].public_status == "confirmed_public"
    assert points[0].latitude == 30.01


def test_upsert_access_points_is_idempotent(db_session):
    tx = _tx_state(db_session)
    target = _target(
        access_points=(NamedAccessPoint("Test Park Boat Ramp", 30.01, -96.01, "boat_ramp"),)
    )
    wb = upsert_waterbody(db_session, target, tx)
    upsert_access_points(db_session, wb, target, datetime.now(timezone.utc))
    upsert_access_points(db_session, wb, target, datetime.now(timezone.utc))  # re-run
    db_session.flush()

    points = db_session.query(AccessPoint).filter_by(waterbody_id=wb.id).all()
    assert len(points) == 1  # not duplicated


def test_upsert_access_points_never_writes_confirmed_public_for_a_closed_lake(db_session):
    # Defensive test: even if access_points were accidentally non-empty on
    # a closed lake, PRD §12 says never present that as public access.
    tx = _tx_state(db_session)
    target = _target(
        public_access_status="closed",
        access_points=(NamedAccessPoint("TMPA Park", 30.6, -96.0, "boat_ramp"),),
    )
    wb = upsert_waterbody(db_session, target, tx)
    written = upsert_access_points(db_session, wb, target, datetime.now(timezone.utc))
    db_session.flush()

    assert written == 0
    assert db_session.query(AccessPoint).filter_by(waterbody_id=wb.id).count() == 0


def test_ingest_one_lake_writes_access_points_even_when_no_species_mentions_found(
    db_session, monkeypatch
):
    import app.data_import.tpwd_lake_survey_scraper as scraper_module

    monkeypatch.setattr(
        scraper_module, "fetch_report_html", lambda url, user_agent: "<html><body>no fish here</body></html>"
    )
    tx = _tx_state(db_session)
    target = _target(
        access_points=(NamedAccessPoint("Test Park Boat Ramp", 30.01, -96.01, "boat_ramp"),)
    )

    result = ingest_one_lake(db_session, target, tx, "test-agent")

    assert result.status == "no_mentions"
    assert result.access_points_written == 1
    wb = db_session.query(Waterbody).filter_by(name="Test Lake").first()
    assert wb is not None  # waterbody still created despite 0 species mentions
    assert db_session.query(AccessPoint).filter_by(waterbody_id=wb.id).count() == 1


def test_upsert_waterbody_promotes_a_same_named_osm_lake_and_drops_its_osm_entrances(db_session):
    """If the statewide OpenStreetMap layer already imported a lake under
    the exact name TPWD uses, the scraper must not write verified data into
    a row still labelled 'osm' (see osm_waterbody_import.py)."""
    tx = _tx_state(db_session)
    osm_row = Waterbody(
        state_id=tx.id,
        name="Test Lake",
        latitude=30.0,
        longitude=-96.0,
        access_summary="osm",
        source_url="https://www.openstreetmap.org/way/9",
        source_updated_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        data_tier="osm",
        public_access_status="unknown",
        osm_ref="way/9",
    )
    osm_row.access_points = [
        AccessPoint(
            name="Boat ramp (OpenStreetMap)",
            latitude=30.0,
            longitude=-96.0,
            access_type="boat_ramp",
            public_status="osm_reported",
            osm_ref="node/9",
        )
    ]
    db_session.add(osm_row)
    db_session.flush()

    wb = upsert_waterbody(db_session, _target(), tx)

    assert wb.id == osm_row.id
    assert wb.data_tier == "verified"
    assert wb.osm_ref == "way/9"  # kept, so the next OSM import leaves it alone
    assert wb.public_access_status == "open"
    assert [ap.public_status for ap in wb.access_points] == []
