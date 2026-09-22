"""Tests for the TPWD scraper's parsing logic. Deliberately network-free —
see the scraper's module docstring for why real HTTP calls don't belong in
a test suite that runs on every commit. Uses a real (saved) excerpt of the
Lake Somerville survey report page as a fixture so the parsing logic is
tested against actual TPWD prose, not an idealized sentence.
"""
from app.data_import.tpwd_lake_survey_scraper import (
    KNOWN_SPECIES,
    extract_species_mentions,
    fetch_report_html,
    page_text,
)

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
