"""TPWD's lake pages and survey reports (tpwd_pages.py) and the statewide
import built on them (tpwd_statewide_import.py). The HTML here copies the
structure of TPWD's real pages, cut down."""
import json
from datetime import datetime
from pathlib import Path

import pytest

from app.data_import import tpwd_statewide_import as imp
from app.data_import.tpwd_pages import parse_lake_page, parse_report_page, species_in_phrase
from app.models.waterbody import AccessPoint, AgencyLakeProfile, Species, State, Waterbody, WaterbodySpecies


def lake_html(name: str, report_id: str = "pwd_rp_t3200_1374", species=None, ratings=None, acres="11,456") -> str:
    species = species if species is not None else [
        "Largemouth bass", "White &amp; hybrid striped bass", "Channel, blue &amp; flathead catfish", "Crappie",
    ]
    ratings = ratings if ratings is not None else [("Largemouth Bass", 3), ("Crappie", 2)]
    items = "".join(f"<li><a href='#'>{s}</a></li>" for s in species)
    rows = "".join(
        f"<tr><th scope='row'>{label}</th>"
        + "".join("<td><img alt='yes' src='x.gif'/></td>" if i == col else "<td>&nbsp;</td>" for i in range(4))
        + "</tr>"
        for label, col in ratings
    )
    return f"""<html><head><title>Fishing {name}</title></head><body>
<nav>menu</nav><main>
<p>Location: On Yegua Creek in Washington County, 30 miles from Bryan<br/>
Surface area: {acres} acres<br/>Maximum depth: 38 feet<br/>Impounded: 1967</p>
<h6>Predominant Fish Species</h6><ul>{items}</ul>
<p><a href="../../../action/stock_bywater.php?WB_code=0680">Stocking History</a>
<a href="/publications/pwdpubs/lake_survey/{report_id}/">Latest Survey Report</a></p>
<table id="Ratings"><tr><th>Species</th><th>Poor</th><th>Fair</th><th>Good</th><th>Excellent</th></tr>{rows}</table>
</main></body></html>"""


def report_html(name: str, body: str) -> str:
    return f"""<html><body><main>
<div class="sidebar"><p>Other Lakes: Lake Fork, Toledo Bend</p></div>
<h1>{name} - 2020 Survey Report</h1>
<h3>Fish Community</h3><p>{body}</p>
</main></body></html>"""


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrase, expected",
    [
        ("Channel, blue & flathead catfish", ["Channel Catfish", "Blue Catfish"]),
        ("White & hybrid striped bass", ["White Bass", "Hybrid Striped Bass"]),
        ("Black & white crappie", ["Black Crappie", "White Crappie"]),
        ("Striped & hybrid striped bass", ["Striped Bass", "Hybrid Striped Bass"]),
        ("Sunshine bass (hybrid)", ["Hybrid Striped Bass"]),
        ("Bluegill & redear sunfish", ["Bluegill"]),
        ("Largemouth , Smallmouth , and Spotted bass", ["Largemouth Bass", "Spotted Bass"]),
        # A generic group names no particular species.
        ("Crappie", []),
        ("Catfish", []),
        # "white" + "striped bass" is not a fish.
        ("White & striped bass", ["White Bass", "Striped Bass"]),
    ],
)
def test_species_in_a_tpwd_list_item(phrase, expected):
    assert species_in_phrase(phrase) == expected


def test_parse_lake_page():
    page = parse_lake_page(lake_html("Lake Somerville"), "somerville")
    assert page.name == "Lake Somerville"
    assert page.url == "https://tpwd.texas.gov/fishboat/fish/recreational/lakes/somerville/"
    assert page.access_url.endswith("/somerville/access.phtml")
    assert page.report_id == "pwd_rp_t3200_1374"
    assert page.wb_code == "0680"
    assert page.location.startswith("On Yegua Creek in Washington County")
    assert (page.surface_acres, page.max_depth_ft, page.impounded) == (11456, 38, "1967")
    assert page.predominant[0] == "Largemouth bass"
    assert set(page.species) == {"Largemouth Bass", "White Bass", "Hybrid Striped Bass", "Channel Catfish", "Blue Catfish"}
    assert [(r.label, r.rating) for r in page.ratings] == [("Largemouth Bass", "Excellent"), ("Crappie", "Good")]


def test_a_rating_row_with_two_marks_is_skipped_not_guessed():
    html = lake_html("Lake X").replace(
        "</table>",
        "<tr><th scope='row'>Sunfish</th><td><img/></td><td><img/></td><td></td><td></td></tr></table>",
    )
    assert [r.label for r in parse_lake_page(html, "x").ratings] == ["Largemouth Bass", "Crappie"]


def test_report_mentions_are_presence_only():
    report = parse_report_page(
        report_html(
            "Lake Somerville",
            "Important sport fishes include Channel Catfish and Hybrid Striped Bass. "
            "No White Crappie were collected during sampling. "
            "Spotted Bass stocking was discontinued in 2017. "
            "Gizzard Shad were abundant.",
        ),
        "pwd_rp_t3200_1374",
    )
    assert (report.lake_name, report.year) == ("Lake Somerville", 2020)
    names = [m.species_name for m in report.mentions]
    assert names == ["Channel Catfish", "Hybrid Striped Bass", "Gizzard Shad"]
    # The sidebar's list of other lakes is not part of the report.
    assert all("Toledo" not in m.evidence_sentence for m in report.mentions)


# --------------------------------------------------------------------------
# Import
# --------------------------------------------------------------------------


@pytest.fixture()
def state(db_session):
    tx = State(name="Texas", code="TX", official_source_url="https://tpwd.texas.gov")
    db_session.add(tx)
    db_session.flush()
    return tx


def osm_lake(db, state, name, lat, lng, ref, with_entrance=True):
    wb = Waterbody(
        state_id=state.id, name=name, latitude=lat, longitude=lng, access_summary="osm",
        source_url="https://www.openstreetmap.org/" + ref, source_updated_at=datetime(2026, 1, 1),
        data_tier="osm", public_access_status="unknown", osm_ref=ref, water_type="reservoir",
    )
    db.add(wb)
    db.flush()
    if with_entrance:
        db.add(AccessPoint(
            waterbody_id=wb.id, name="Slipway", latitude=lat, longitude=lng,
            access_type="boat_ramp", public_status="osm_reported", osm_ref=ref + "/ramp",
        ))
        db.flush()
    return wb


def ramp(pwaid, lake, lat, lng):
    return imp.Ramp(pwaid, lake, lat, lng, f"county{pwaid:03d}")


def write_cache(tmp_path: Path, lakes: dict[str, str], reports: dict[str, str]) -> Path:
    for slug, html in lakes.items():
        (tmp_path / f"lake__{slug}.html").write_text(html, encoding="utf-8")
    for rid, html in reports.items():
        (tmp_path / f"report__{rid}.html").write_text(html, encoding="utf-8")
    return tmp_path


SOMERVILLE_REPORT = report_html(
    "Lake Somerville", "Important sport fishes include Channel Catfish and Hybrid Striped Bass. Gizzard Shad were abundant."
)


def test_a_lake_is_placed_on_the_same_named_lake_near_its_ramps(db_session, state, tmp_path):
    near = osm_lake(db_session, state, "Somerville Lake", 30.34, -96.54, "way/1")
    far = osm_lake(db_session, state, "Lake Somerville", 33.0, -101.0, "way/2")
    cache = write_cache(tmp_path, {"somerville": lake_html("Lake Somerville")}, {"pwd_rp_t3200_1374": SOMERVILLE_REPORT})
    ramps = [
        ramp(1, "Lake Somerville", 30.31, -96.62),
        ramp(2, "Somerville Lake", 30.30, -96.57),
        ramp(3, "Lake Somerville", 33.5, -97.0),  # mislabelled: hundreds of km away
    ]
    summary = imp.run(db_session, cache, ramps)

    assert dict(summary.placed) == {"osm_name": 1}
    db_session.refresh(near)
    assert near.data_tier == "verified" and near.name == "Lake Somerville"
    assert near.source_url.endswith("/lakes/somerville/")
    assert far.data_tier == "osm"
    statuses = sorted((ap.osm_ref, ap.public_status) for ap in near.access_points)
    # TPWD's two nearby ramps replace OpenStreetMap's slipway; the far one is dropped.
    assert statuses == [("tpwd_ramp/1", "confirmed_public"), ("tpwd_ramp/2", "confirmed_public")]
    assert near.public_access_status == "open"


def test_species_come_from_the_report_then_the_lake_page(db_session, state, tmp_path):
    wb = osm_lake(db_session, state, "Lake Somerville", 30.34, -96.54, "way/1")
    cache = write_cache(tmp_path, {"somerville": lake_html("Lake Somerville")}, {"pwd_rp_t3200_1374": SOMERVILLE_REPORT})
    imp.run(db_session, cache, [ramp(1, "Lake Somerville", 30.33, -96.55)])

    links = {link.species.common_name: link for link in db_session.query(WaterbodySpecies).filter_by(waterbody_id=wb.id)}
    assert set(links) == {
        "Channel Catfish", "Hybrid Striped Bass", "Gizzard Shad",  # report
        "Largemouth Bass", "White Bass", "Blue Catfish",  # lake page list
    }
    assert all(link.confidence == "confirmed" for link in links.values())
    assert links["Channel Catfish"].source_url.endswith("/pwd_rp_t3200_1374/")
    assert links["Channel Catfish"].observed_at == datetime(2020, 1, 1)
    assert "predominant fish species" in links["Blue Catfish"].evidence
    assert links["Blue Catfish"].source_url.endswith("/lakes/somerville/")
    assert "Striped Bass" not in links  # "hybrid striped bass" is not "striped bass"


def test_the_profile_keeps_tpwds_own_words(db_session, state, tmp_path):
    wb = osm_lake(db_session, state, "Lake Somerville", 30.34, -96.54, "way/1")
    cache = write_cache(tmp_path, {"somerville": lake_html("Lake Somerville")}, {"pwd_rp_t3200_1374": SOMERVILLE_REPORT})
    imp.run(db_session, cache, [])
    profile = db_session.query(AgencyLakeProfile).one()
    assert profile.waterbody_id == wb.id
    assert (profile.agency, profile.agency_lake_id, profile.placement) == ("tpwd", "somerville", "osm_name_only")
    assert profile.ratings == [{"label": "Largemouth Bass", "rating": "Excellent"}, {"label": "Crappie", "rating": "Good"}]
    assert profile.predominant_species[-1] == "Crappie"
    assert (profile.surface_acres, profile.survey_year) == (11456, 2020)


def test_without_ramps_a_lake_keeps_its_openstreetmap_entrances(db_session, state, tmp_path):
    wb = osm_lake(db_session, state, "Lake Somerville", 30.34, -96.54, "way/1")
    cache = write_cache(tmp_path, {"somerville": lake_html("Lake Somerville")}, {})
    imp.run(db_session, cache, [])
    db_session.refresh(wb)
    assert [ap.public_status for ap in wb.access_points] == ["osm_reported"]
    assert wb.public_access_status == "unknown"
    assert "no ramp" in wb.access_summary


def test_same_name_without_ramps_is_left_out_when_ambiguous(db_session, state, tmp_path):
    osm_lake(db_session, state, "Moss Lake", 33.7, -97.2, "way/1")
    osm_lake(db_session, state, "Moss Lake", 31.0, -96.0, "way/2")
    cache = write_cache(tmp_path, {"moss": lake_html("Moss Lake")}, {})
    summary = imp.run(db_session, cache, [])
    assert summary.placed == {}
    assert summary.unplaced[0][0] == "Moss Lake"
    assert db_session.query(Waterbody).filter_by(data_tier="verified").count() == 0


def test_a_known_wrong_namesake_is_left_out(db_session, state, tmp_path):
    osm_lake(db_session, state, "Lone Star Lake", 32.7, -98.5, "way/1")
    cache = write_cache(tmp_path, {"lone_star": lake_html("Lone Star Lake")}, {})
    summary = imp.run(db_session, cache, [])
    assert summary.placed == {} and "Morris County" in summary.unplaced[0][1]


def test_ramps_without_an_openstreetmap_lake_create_one_at_the_ramps(db_session, state, tmp_path):
    cache = write_cache(tmp_path, {"clyde": lake_html("Lake Clyde", acres="449")}, {})
    summary = imp.run(db_session, cache, [ramp(1, "Lake Clyde", 32.30, -99.47), ramp(2, "Lake Clyde", 32.32, -99.48)])
    assert dict(summary.placed) == {"ramps": 1}
    wb = db_session.query(Waterbody).filter_by(name="Lake Clyde").one()
    assert wb.data_tier == "verified" and wb.osm_ref is None
    assert (round(wb.latitude, 2), round(wb.longitude, 3)) == (32.31, -99.475)
    assert wb.agency_profile.placement == "ramps"


def test_a_curated_lake_keeps_its_name_and_access_and_gains_only_new_ramps(db_session, state, tmp_path):
    wb = Waterbody(
        state_id=state.id, name="Lake Fork", latitude=32.8, longitude=-95.59, access_summary="curated",
        source_url="https://tpwd.texas.gov/fishboat/fish/recreational/lakes/fork/", source_updated_at=datetime(2026, 1, 1),
        data_tier="verified", public_access_status="open", osm_ref="way/9",
    )
    db_session.add(wb)
    db_session.flush()
    db_session.add(AccessPoint(
        waterbody_id=wb.id, name="Oak Ridge Marina", latitude=32.8000, longitude=-95.6000,
        access_type="boat_ramp", public_status="confirmed_public",
    ))
    curated = Species(common_name="Bluegill", scientific_name="Lepomis macrochirus", difficulty="beginner", profile="x")
    db_session.add(curated)
    db_session.flush()
    db_session.add(WaterbodySpecies(
        waterbody_id=wb.id, species_id=curated.id, confidence="confirmed", evidence="hand-checked",
        source_url="https://example.org/fork", observed_at=datetime(2025, 1, 1),
    ))
    db_session.flush()
    cache = write_cache(tmp_path, {"fork": lake_html("Lake Fork", acres="27,264")}, {})
    ramps = [ramp(1, "Lake Fork", 32.8005, -95.6005), ramp(2, "Lake Fork", 32.85, -95.55)]
    summary = imp.run(db_session, cache, ramps)

    db_session.refresh(wb)
    assert dict(summary.placed) == {"existing": 1}
    assert (wb.name, wb.access_summary) == ("Lake Fork", "curated")
    names = sorted(ap.name for ap in wb.access_points)
    # Ramp 1 is 70 m from the curated marina: the same place, not added again.
    assert names == ["Oak Ridge Marina", "Public boat ramp (TPWD #2)"]
    assert summary.ramps_skipped_duplicate == 1
    # Hand-curated species from another source stay.
    assert any(link.source_url == "https://example.org/fork" for link in wb.species_links)


def test_a_closed_lake_gets_no_ramps(db_session, state, tmp_path):
    wb = osm_lake(db_session, state, "Gibbons Creek Reservoir", 30.62, -96.04, "way/1", with_entrance=False)
    wb.public_access_status = "closed"
    db_session.flush()
    cache = write_cache(tmp_path, {"gibbons": lake_html("Gibbons Creek Reservoir")}, {})
    imp.run(db_session, cache, [ramp(1, "Gibbons Creek Reservoir", 30.62, -96.05)])
    db_session.refresh(wb)
    assert wb.access_points == []


def test_rerunning_changes_nothing(db_session, state, tmp_path):
    osm_lake(db_session, state, "Lake Somerville", 30.34, -96.54, "way/1")
    cache = write_cache(
        tmp_path,
        {"somerville": lake_html("Lake Somerville"), "clyde": lake_html("Lake Clyde", acres="449")},
        {"pwd_rp_t3200_1374": SOMERVILLE_REPORT},
    )
    ramps = [ramp(1, "Lake Somerville", 30.33, -96.55), ramp(2, "Lake Clyde", 32.30, -99.47)]

    def snapshot():
        return (
            db_session.query(Waterbody).count(),
            db_session.query(AccessPoint).count(),
            db_session.query(WaterbodySpecies).count(),
            sorted((p.agency_lake_id, p.placement) for p in db_session.query(AgencyLakeProfile)),
        )

    first = imp.run(db_session, cache, ramps)
    before = snapshot()
    second = imp.run(db_session, cache, ramps)
    assert snapshot() == before
    assert dict(second.placed) == dict(first.placed) == {"osm_name": 1, "ramps": 1}


def test_load_ramps_keeps_lake_ramps_only(tmp_path):
    def feature(pwaid, kind, name, lng, lat):
        return {
            "type": "Feature",
            "properties": {"PWAID": pwaid, "TPWAID": f"x{pwaid}", "AccessType": kind, "AccessTypeDescription": name},
            "geometry": {"type": "Point", "coordinates": [lng, lat]},
        }

    path = tmp_path / "ramps.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": [
        feature(1, "Lake/Reservoir", "Lake Fork", -95.6, 32.8),
        feature(2, "River/Stream", "Trinity River", -96.0, 32.0),
        feature(3, "Bay/Beach", "Galveston Bay", -94.9, 29.4),
        feature(4, "Lake/Reservoir", "", -95.0, 32.0),
    ]}))
    assert imp.load_ramps(path) == [imp.Ramp(1, "Lake Fork", 32.8, -95.6, "x1")]


def test_search_radius_grows_with_the_lake():
    assert imp.search_radius_km(None) == 8.0
    assert 26 < imp.search_radius_km(11_456) < 28  # Lake Somerville
    assert 105 < imp.search_radius_km(181_600) < 112  # Toledo Bend


def test_the_lake_detail_api_includes_the_agency_profile(client, db_session, state, tmp_path):
    wb = osm_lake(db_session, state, "Lake Somerville", 30.34, -96.54, "way/1")
    cache = write_cache(tmp_path, {"somerville": lake_html("Lake Somerville")}, {"pwd_rp_t3200_1374": SOMERVILLE_REPORT})
    imp.run(db_session, cache, [ramp(1, "Lake Somerville", 30.33, -96.55)])
    db_session.commit()

    body = client.get(f"/api/waterbodies/{wb.id}").json()
    assert body["data_tier"] == "verified"
    profile = body["agency_profile"]
    assert profile["agency"] == "tpwd" and profile["survey_year"] == 2020
    assert profile["ratings"][0] == {"label": "Largemouth Bass", "rating": "Excellent"}
    assert profile["survey_report_url"].endswith("/pwd_rp_t3200_1374/")
    assert body["access_points"][0]["public_status"] == "confirmed_public"


def test_a_lake_without_a_profile_has_none(client, db_session, state):
    wb = osm_lake(db_session, state, "Some Pond", 30.0, -96.0, "way/7")
    db_session.commit()
    assert client.get(f"/api/waterbodies/{wb.id}").json()["agency_profile"] is None


def test_limited_numbers_is_still_presence_but_a_length_limit_is_not():
    report = parse_report_page(
        report_html(
            "Lake Bryan",
            "Gizzard Shad are present in limited numbers. "
            "The 14-inch minimum length limit for Largemouth Bass was removed.",
        ),
        "pwd_rp_t3200_1257",
    )
    assert [m.species_name for m in report.mentions] == ["Gizzard Shad"]
