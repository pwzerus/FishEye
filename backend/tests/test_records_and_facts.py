"""State records and ShareLunker as presence evidence
(app/data_import/record_fish_import.py), the facts-only migration
(app/cli/facts_only.py) and the species-name table. Network-free."""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select

from app.cli import facts_only
from app.data_import import osm_waterbody_import as osm
from app.data_import import record_fish_import as rec
from app.data_import.species_names import by_scientific_name, canonical, species_list
from app.models.waterbody import (
    AgencyLakeProfile,
    Species,
    SpeciesEvidence,
    State,
    Waterbody,
    WaterbodySpecies,
)
from tests.test_osm_import import _lake

NOW = datetime(2026, 10, 26)

WATER_RECORDS_HTML = """
<h1><a href="../programs/fishrecords/"><img src="x.jpg"/></a> Water Body Records for Lake Fork</h1>
<h2>Weight Records</h2>
<table><tr><th>Species</th><th>Weight</th><th>Length</th><th>Date</th><th>Angler</th><th>Bait or Lure</th></tr>
<tr><td>Bass, Largemouth</td><td>18.18</td><td>25.50</td><td>Jan 24, 1992</td><td>A. Angler</td><td>shiner</td></tr>
<tr><td>Crappie, White</td><td>3.10</td><td>&nbsp;</td><td>Mar 2, 2021</td><td>B. Angler</td><td>jig</td></tr>
<tr><td>Bass, Guadalupe x Largemouth</td><td>4.46</td><td>&nbsp;</td><td>Jul 26, 2026</td><td>C. Angler</td><td></td></tr>
</table>"""


def _tx(db):
    osm.run("TX", {"elements": [
        _lake(1, "Lake Fork Reservoir", 32.85, -95.55, 0.1),
        _lake(2, "O. H. Ivie Reservoir", 31.55, -99.70, 0.1),
        _lake(3, "Moss Lake", 33.70, -97.20, 0.01),
        _lake(4, "Moss Lake", 31.00, -96.00, 0.01),
    ]}, db)


def _named(db, name):
    return db.scalars(select(Waterbody).where(Waterbody.name == name)).first()


def test_a_water_records_page_gives_only_species_and_year():
    lake, rows = rec.parse_water_records(WATER_RECORDS_HTML)
    assert lake == "Lake Fork"
    assert rows == [("Bass, Largemouth", 1992), ("Crappie, White", 2021), ("Bass, Guadalupe x Largemouth", 2026)]


def test_a_name_of_qualifiers_only_matches_no_lake(db_session):
    osm.run("TX", {"elements": [
        _lake(1, "Upper Lake", 31.51, -95.09, 0.01), _lake(2, "Upper Lake Avery", 31.05, -95.13, 0.01),
    ]}, db_session)
    names = rec.LakeNames(list(db_session.scalars(select(Waterbody))))
    assert names.find("Upper Lake") == (None, "name too general")
    assert names.find("Upper Lake Avery")[0].name == "Upper Lake Avery"


def test_a_park_name_matches_the_lake_in_it_not_a_reordered_name(db_session):
    osm.run("TX", {"elements": [
        _lake(1, "Spring Park Lake", 31.76, -95.61, 0.01), _lake(2, "Spring Lake", 33.46, -94.06, 0.01),
        _lake(3, "Alvarado Park Lake", 32.40, -97.21, 0.01),
    ]}, db_session)
    names = rec.LakeNames(list(db_session.scalars(select(Waterbody))))
    assert names.find("Spring Lake Park")[0].name == "Spring Lake"
    assert names.find("Alvarado Park")[0].name == "Alvarado Park Lake"


def test_a_region_list_gives_each_water_bodys_code():
    html = '<a href="../../action/waterecords.php?WB_code=0001">Abilene</a> <a href="../../action/waterecords.php?WB_code=0006">Alan Henry</a>'
    assert rec.parse_region_page(html) == [("0001", "Abilene"), ("0006", "Alan Henry")]


def test_texas_records_and_sharelunker_become_evidence_without_personal_data(db_session, tmp_path):
    _tx(db_session)
    (tmp_path / "tpwd_water_records.json").write_text(json.dumps({"fetched_at": "2026-10-26T18:00:00+00:00", "lakes": {
        "0221": {"water": "Lake Fork", "url": "https://tpwd.texas.gov/fishboat/fish/action/waterecords.php?WB_code=0221",
                 "records": [{"species": s, "year": y} for s, y in rec.parse_water_records(WATER_RECORDS_HTML)[1]]},
        "0900": {"water": "Brazos River", "url": "u", "records": [{"species": "Bass, Striped", "year": 1999}]},
    }}))
    (tmp_path / "sharelunker.json").write_text(json.dumps({"fetched_at": "2026-10-26T18:08:34Z", "rows": [
        {"catch_id": "1", "lake_name": "O. H. Ivie", "water_other": None, "entry_class": "Lunker", "year": 2024},
        {"catch_id": "2", "lake_name": "O. H. Ivie", "water_other": None, "entry_class": "Elite", "year": 2026},
        {"catch_id": "3", "lake_name": "Moss", "water_other": None, "entry_class": "Lunker", "year": 2020},
        {"catch_id": "4", "lake_name": "NULL", "water_other": "Private Lake", "entry_class": "Lunker", "year": 2019},
    ]}))
    out = rec.run(db_session, "TX", tmp_path, now=NOW)

    fork = _named(db_session, "Lake Fork Reservoir")
    by_species = {e.species.common_name: e for e in fork.species_evidence}
    assert set(by_species) == {"Largemouth Bass", "White Crappie"}  # the hybrid isn't mapped
    assert by_species["White Crappie"].evidence == "TPWD's water body records for this lake include a White Crappie from 2021."
    assert by_species["White Crappie"].kind == "record"
    # Before 2000: reported, not confirmed.
    links = {link.species.common_name: link.confidence for link in fork.species_links}
    assert links == {"Largemouth Bass": "reported", "White Crappie": "confirmed"}

    ivie = _named(db_session, "O. H. Ivie Reservoir")
    [e] = ivie.species_evidence
    assert e.evidence == "TPWD's Toyota ShareLunker program has entries of Largemouth Bass from this lake (most recent 2026)."
    assert e.year == 2026

    unmatched = out["sharelunker"].unmatched + out["tpwd_records"].unmatched
    assert any(u.startswith("Moss (1 entries): ambiguous") for u in unmatched)
    assert any("Private Lake" in u and "no specific lake" in u for u in unmatched)
    assert any(u.startswith("Brazos River") and "river" in u for u in unmatched)

    # Nothing personal anywhere in what was stored.
    for text in [e.evidence for e in db_session.scalars(select(SpeciesEvidence))]:
        assert "Angler" not in text and "shiner" not in text and "18.18" not in text


def test_georgia_and_california_lists(db_session, tmp_path):
    osm.run("GA", {"elements": [_lake(1, "Lake Chatuge", 34.95, -83.80, 0.05)]}, db_session)
    (tmp_path / "ga_records.json").write_text(json.dumps({"rows": [
        {"species": "Bass, Hybrid", "water": "Lake Chatuge", "year": 1995},
        {"species": "Sunfish, Green", "water": "Private pond", "year": 2000},
    ]}))
    out = rec.run(db_session, "GA", tmp_path, now=NOW)["ga_records"]
    [e] = _named(db_session, "Lake Chatuge").species_evidence
    assert e.evidence == "Georgia WRD's state record list includes a Hybrid Striped Bass from this lake (1995)."
    assert out.unmatched == ["Green Sunfish at Private pond: no specific lake named"]

    osm.run("CA", {"elements": [_lake(5, "Castaic Lake", 34.52, -118.61, 0.02)]}, db_session)
    (tmp_path / "ca_records.json").write_text(json.dumps({"rows": [
        {"species": "bass, largemouth", "scientific_name": "", "water": "Castaic Lake at the main boat ramp",
         "county": "Los Angeles", "year": 1991, "fishing_type": "Freshwater Angling"},
        {"species": "halibut, California", "water": "Santa Monica Bay", "county": "Los Angeles", "year": 1999,
         "fishing_type": "Ocean Angling"},
    ]}))
    out = rec.run(db_session, "CA", tmp_path, now=NOW, cdfw_cache=tmp_path)["ca_records"]
    [e] = _named(db_session, "Castaic Lake").species_evidence
    assert (e.species.common_name, e.year, e.source) == ("Largemouth Bass", 1991, "ca_records")
    assert out.read == 1  # ocean rows are not read


def test_species_names_from_every_list_agree():
    assert canonical("Bass, Largemouth")[0] == canonical("Large mouth bass")[0] == "Largemouth Bass"
    assert canonical("catfish, bullhead, brown")[0] == "Brown Bullhead"
    assert canonical("Eagle Lake Trout")[0] == "Rainbow Trout"
    assert canonical("Bass, Guadalupe x Largemouth") is None
    assert canonical("Minnow, golden shiner") is None
    assert by_scientific_name("Micropterus salmoides") == "Largemouth Bass"
    assert species_list(["Channel & flathead catfish", "White & striped bass", "Sunfish"]) == [
        "Channel Catfish", "Flathead Catfish", "Striped Bass", "Sunfish", "White Bass"]


# ---------------------------------------------------------------- facts only


def test_the_migration_rewrites_tpwd_quotes_and_the_check_finds_none(db_session, tmp_path):
    state = State(name="Texas", code="TX", official_source_url="x")
    db_session.add(state)
    db_session.flush()
    wb = Waterbody(state_id=state.id, name="Lake Fork", latitude=32.8, longitude=-95.5, access_summary="",
                   source_url="x", source_updated_at=NOW, data_tier="verified")
    sp = Species(common_name="Largemouth Bass", scientific_name="", difficulty="beginner", profile="")
    db_session.add_all([wb, sp])
    db_session.flush()
    report = "https://tpwd.texas.gov/publications/pwdpubs/lake_survey/pwd_rp_t3200_1291/"
    quote = "Largemouth Bass abundance was much higher in 2019 than in 2021 at every station."
    db_session.add(WaterbodySpecies(waterbody_id=wb.id, species_id=sp.id, confidence="confirmed",
                                    evidence=quote, source_url=report, observed_at=NOW))
    db_session.add(AgencyLakeProfile(
        waterbody_id=wb.id, agency="tpwd", agency_lake_id="fork", agency_name="Lake Fork", page_url="p",
        survey_report_url=report, survey_year=2021, location="On Lake Fork Creek 5 miles west of Quitman",
        predominant_species=["White & striped bass"], ratings=[], placement="osm_name", retrieved_at=NOW))
    db_session.flush()
    cache = tmp_path / "tpwd_cache"
    cache.mkdir()
    (cache / "report__x.html").write_text(f"<p>{quote}</p><p>On Lake Fork Creek 5 miles west of Quitman</p>")

    assert facts_only.check(db_session, (cache,))  # the quote is found
    counts = facts_only.rewrite(db_session)
    assert counts == {"tpwd_evidence": 1, "tpwd_locations": 1, "species_lists": 1}
    link = db_session.get(WaterbodySpecies, (wb.id, sp.id))
    assert link.evidence == "TPWD's 2021 survey report for this lake records Largemouth Bass."
    profile = db_session.scalars(select(AgencyLakeProfile)).one()
    assert profile.location is None and profile.predominant_species == ["Striped Bass", "White Bass"]
    assert facts_only.check(db_session, (cache,)) == []
    # A TPWD water body records link already carries our sentence: left alone.
    other = Species(common_name="White Crappie", scientific_name="", difficulty="beginner", profile="")
    db_session.add(other)
    db_session.flush()
    ours = "TPWD's water body records for this lake include a White Crappie from 2021."
    db_session.add(WaterbodySpecies(waterbody_id=wb.id, species_id=other.id, confidence="confirmed", evidence=ours,
                                    source_url="https://tpwd.texas.gov/fishboat/fish/action/waterecords.php?WB_code=0221",
                                    observed_at=NOW))
    db_session.flush()
    facts_only.rewrite(db_session)
    assert db_session.get(WaterbodySpecies, (wb.id, other.id)).evidence == ours
    assert facts_only.rewrite(db_session) == {"tpwd_evidence": 0, "tpwd_locations": 0, "species_lists": 0}
