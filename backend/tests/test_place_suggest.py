"""Place suggestions as you type (services/place_suggest.py, GET
/api/places/suggest) and the list they come from (app/cli/us_places.py).
Network-free: the ranking tests use a few hand-made places, the builder
tests tiny Census-format files, and the API the list shipped in app/data."""
import zipfile

import pytest

from app.cli import us_places
from app.services.place_suggest import Place, PlaceIndex, plain, shortened


def place(name, state, pop, kind="place", lat=30.0, lon=-97.0, near=""):
    return Place(kind, name, state, lat, lon, pop, near)


@pytest.fixture()
def index():
    return PlaceIndex([
        place("Austin", "TX", 979_539, lat=30.30, lon=-97.75),
        place("Austin", "MN", 26_358, lat=43.67, lon=-92.98),
        place("Austintown", "OH", 29_000),
        place("Austin County", "TX", 30_000, kind="county"),
        place("San Francisco", "CA", 808_000),
        place("St. Louis", "MO", 293_000),
        place("St. Louis County", "MO", 1_000_000, kind="county"),
        place("Saint Paul", "MN", 303_000),
        place("Fort Worth", "TX", 956_000),
        place("Springfield", "IL", 114_000, lat=39.80, lon=-89.64),
        place("Springfield", "MA", 155_000, lat=42.11, lon=-72.54),
        place("Española", "NM", 10_000),
        place("78701", "TX", 11_824, kind="zip", near="Austin"),
        place("78745", "TX", 60_000, kind="zip", near="Austin"),
        place("78701", "XX", 0, kind="zip", near="Elsewhere"),
    ])


def labels(found):
    return [p.label for p in found]


def test_a_start_of_the_name_finds_the_biggest_first(index):
    assert labels(index.suggest("aus"))[:3] == ["Austin, TX", "Austintown, OH", "Austin, MN"]


def test_a_later_word_is_found_too(index):
    assert labels(index.suggest("fran")) == ["San Francisco, CA"]


def test_saint_mount_and_fort_read_like_their_short_forms(index):
    assert plain("St. Louis") == "st louis"
    assert shortened("saint paul") == "st paul"
    assert labels(index.suggest("saint lo"))[0] == "St. Louis, MO"
    assert labels(index.suggest("st pa")) == ["Saint Paul, MN"]
    assert labels(index.suggest("ft wor")) == ["Fort Worth, TX"]
    assert labels(index.suggest("for")) == ["Fort Worth, TX"]


def test_a_county_comes_after_a_town_of_its_name(index):
    assert labels(index.suggest("st lou")) == ["St. Louis, MO", "St. Louis County, MO"]


def test_the_map_state_and_where_it_looks_lift_a_name(index):
    assert labels(index.suggest("austin", prefer_state="MN"))[0] == "Austin, MN"
    assert labels(index.suggest("springf", near=(39.8, -89.6)))[0] == "Springfield, IL"
    assert labels(index.suggest("springf", near=(42.1, -72.6)))[0] == "Springfield, MA"


def test_a_state_typed_keeps_only_its_names(index):
    assert labels(index.suggest("austin", state="tx")) == ["Austin, TX", "Austin County, TX"]


def test_accents_and_case_dont_matter(index):
    assert labels(index.suggest("ESPANOLA")) == ["Española, NM"]


def test_digits_find_zip_codes(index):
    assert labels(index.suggest("787")) == ["78745 (Austin, TX)", "78701 (Austin, TX)", "78701 (Elsewhere, XX)"]
    assert labels(index.suggest("78701"))[0] == "78701 (Austin, TX)"
    assert labels(index.suggest("78701", state="XX")) == ["78701 (Elsewhere, XX)"]
    assert index.suggest("78") == []


def test_too_little_typed_finds_nothing(index):
    assert index.suggest("a") == []
    assert index.suggest(" ,. ") == []
    assert index.suggest("zzzz") == []


def test_the_limit(index):
    assert len(index.suggest("aus", limit=2)) == 2


# ---- the list (app/cli/us_places.py)


def test_the_kind_of_place_comes_off_census_names():
    assert us_places.plain_name("Boise City city") == "Boise City"
    assert us_places.plain_name("Nashville-Davidson metropolitan government (balance)") == "Nashville-Davidson"
    assert us_places.plain_name("Lac du Flambeau CDP") == "Lac du Flambeau"
    assert us_places.plain_name("Town 'n' Country CDP") == "Town 'n' Country"
    assert us_places.plain_name("Carson City") == "Carson City"


def _gazetteer(path, header, rows):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(path.with_suffix(".txt").name, "\n".join(["|".join(header), *("|".join(r) for r in rows)]) + "\n")


def test_the_list_is_built_from_census_files(tmp_path):
    place_head = ["USPS", "GEOID", "GEOIDFQ", "ANSICODE", "NAME", "LSAD", "FUNCSTAT", "ALAND", "AWATER",
                  "ALAND_SQMI", "AWATER_SQMI", "INTPTLAT", "INTPTLONG"]
    _gazetteer(tmp_path / us_places.PLACES, place_head, [
        ["TX", "4805000", "1600000US4805000", "0", "Austin city", "25", "A", "0", "0", "0", "0", "30.2986", "-97.7541"],
        ["TX", "4871228", "1600000US4871228", "0", "Sunset Valley city", "25", "A", "0", "0", "0", "0", "30.2286", "-97.8152"],
        ["TN", "4752006", "1600000US4752006", "0", "Nashville-Davidson metropolitan government (balance)", "00", "F",
         "0", "0", "0", "0", "36.1718", "-86.7850"],
        ["TX", "4899999", "1600000US4899999", "0", "Gone city", "25", "I", "0", "0", "0", "0", "30.0", "-97.0"],
        ["PR", "7200001", "1600000US7200001", "0", "Adjuntas zona urbana", "62", "S", "0", "0", "0", "0", "18.16", "-66.72"],
        ["MA", "2500100", "1600000US2500100", "0", "Acton CDP", "57", "S", "0", "0", "0", "0", "42.48", "-71.43"],
    ])
    county_head = ["USPS", "GEOID", "GEOIDFQ", "ANSICODE", "NAME", "ALAND", "AWATER", "ALAND_SQMI", "AWATER_SQMI",
                   "INTPTLAT", "INTPTLONG"]
    _gazetteer(tmp_path / us_places.COUNTIES, county_head, [
        ["TX", "48453", "0500000US48453", "0", "Travis County", "0", "0", "0", "0", "30.2395", "-97.6913"],
        ["VA", "51760", "0500000US51760", "0", "Richmond city", "0", "0", "0", "0", "37.53", "-77.47"],
        ["DC", "11001", "0500000US11001", "0", "District of Columbia", "0", "0", "0", "0", "38.90", "-77.01"],
    ])
    town_head = ["USPS", "GEOID", "GEOIDFQ", "ANSICODE", "NAME", "FUNCSTAT", "ALAND", "AWATER", "ALAND_SQMI",
                 "AWATER_SQMI", "INTPTLAT", "INTPTLONG"]
    _gazetteer(tmp_path / us_places.TOWNS, town_head, [
        ["MA", "2501700380", "0600000US2501700380", "0", "Acton town", "A", "0", "0", "0", "0", "42.49", "-71.44"],
        ["MA", "2501738715", "0600000US2501738715", "0", "Lincoln town", "A", "0", "0", "0", "0", "42.42", "-71.32"],
        ["TX", "4845390000", "0600000US4845390000", "0", "Austin CCD", "S", "0", "0", "0", "0", "30.30", "-97.75"],
    ])
    _gazetteer(tmp_path / us_places.ZIPS, ["GEOID", "GEOIDFQ", "ALAND", "AWATER", "ALAND_SQMI", "AWATER_SQMI",
                                          "INTPTLAT", "INTPTLONG"], [
        ["78745", "860Z200US78745", "0", "0", "0", "0", "30.2063", "-97.7957"],
        ["00601", "860Z200US00601", "0", "0", "0", "0", "18.18", "-66.75"],
    ])
    (tmp_path / us_places.POPULATION).write_text(
        "GEO_ID|B01003_E001|B01003_M001\n1600000US4805000|979539|484\n1600000US4871228|700|50\n"
        "0500000US48453|1330015|-555555555\n860Z200US78745|60000|900\n", encoding="utf-8")

    rows = {(r.kind, r.name, r.state): r for r in us_places.build(tmp_path)}

    assert set(rows) == {
        ("p", "Austin", "TX"), ("p", "Sunset Valley", "TX"), ("p", "Nashville", "TN"), ("p", "Acton", "MA"),
        ("c", "Travis County", "TX"), ("t", "Lincoln", "MA"), ("z", "78745", "TX"),
    }
    assert rows[("p", "Austin", "TX")].population == 979_539
    # The biggest place within 15 km names the ZIP code, not the nearest small one.
    assert rows[("z", "78745", "TX")].near == "Austin"

    out = tmp_path / "us_places.tsv.gz"
    us_places.write(list(rows.values()), out)
    loaded = PlaceIndex.load(out)
    assert [p.label for p in loaded.suggest("nash")] == ["Nashville, TN"]
    assert [p.label for p in loaded.suggest("787")] == ["78745 (Austin, TX)"]


# ---- the API, on the list shipped in app/data


def test_the_api_suggests_from_the_shipped_list(client):
    r = client.get("/api/places/suggest", params={"q": "aus"})
    assert r.status_code == 200
    first = r.json()[0]
    assert first["label"] == "Austin, TX"
    assert first["kind"] == "place"
    assert abs(first["latitude"] - 30.3) < 0.2 and abs(first["longitude"] + 97.75) < 0.2
    assert "max-age" in r.headers["cache-control"]


def test_the_api_takes_the_map_state_and_point(client):
    r = client.get("/api/places/suggest", params={"q": "springfield", "lat": 42.1, "lon": -72.6, "limit": 1})
    assert [p["label"] for p in r.json()] == ["Springfield, MA"]
    r = client.get("/api/places/suggest", params={"q": "austin", "prefer": "mn", "limit": 1})
    assert [p["label"] for p in r.json()] == ["Austin, MN"]
    r = client.get("/api/places/suggest", params={"q": "78701"})
    assert r.json()[0]["label"] == "78701 (Austin, TX)"
