"""What a careless or mischievous person actually sends (the 2026-11-01 pass).
Each of these was a server error or a wrong answer before."""
from __future__ import annotations

import pytest

from app.services import pins as pins_svc
from app.services import word_filter

PW = "correct horse battery staple"


def test_nul_in_any_field_is_refused_not_a_server_error(client):
    """PostgreSQL can't store a NUL and fails the statement; SQLite takes it,
    so only production broke."""
    for method, url, kw in (
        ("POST", "/api/auth/login", {"json": {"email": "a\x00b@example.com", "password": "x"}}),
        ("GET", "/api/waterbodies", {"params": {"state_code": "\x00"}}),
        ("GET", "/api/pins", {"params": {"species": "a\x00b"}}),
        ("GET", "/api/pins/places", {"params": {"species": "\x00"}}),
    ):
        assert client.request(method, url, **kw).status_code in (401, 422), url


def test_a_nul_refusal_is_in_the_visitors_language(client):
    client.cookies.set("fisheye.lang", "zh")
    r = client.get("/api/pins", params={"species": "\x00"})
    assert r.status_code == 422 and "字符" in r.json()["detail"]
    client.cookies.delete("fisheye.lang")


@pytest.mark.parametrize("email", ["a\x00@b.com", "a@b..com", "<script>@b.com", "a@b.com'--", "😀@b.com", "a@-b.com", "a@b.c"])
def test_addresses_mail_could_never_reach_are_refused(client, email):
    r = client.post("/api/auth/register", json={"email": email, "password": PW, "display_name": "Bob"})
    assert r.status_code == 422, email


@pytest.mark.parametrize("email", ["o'brien+fish@sub.example.co.uk", "A.B-C_d@Example.COM", "  me@xn--bcher-kva.example  "])
def test_real_addresses_still_work(client, email):
    r = client.post("/api/auth/register", json={"email": email, "password": PW, "display_name": "Bob"})
    assert r.status_code == 201, r.text


@pytest.mark.parametrize("name", ["FishEye", "fish eye", "Admin", "ADMIN!", "Moderator", "F.i.s.h.E.y.e", "support"])
def test_names_that_read_as_fisheye_itself_are_refused(client, name):
    r = client.post("/api/auth/register", json={"email": "x@example.com", "password": PW, "display_name": name})
    assert r.status_code == 422 and "reserved" in r.json()["detail"]


def test_a_name_that_only_contains_one_is_fine(client):
    r = client.post("/api/auth/register", json={"email": "x@example.com", "password": PW, "display_name": "Admiral Fisheye Fan"})
    assert r.status_code == 201


@pytest.mark.parametrize("bbox", ["", "nan,nan,nan,nan", "inf,-inf,inf,-inf", "1,2,3", "a,b,c,d"])
def test_a_bad_map_box_is_refused(client, bbox):
    assert client.get("/api/pins/waters", params={"bbox": bbox}).status_code == 422


@pytest.mark.parametrize("bbox", ["nan,nan,nan,nan", "inf,-inf,inf,-inf"])
def test_a_bad_lake_or_shop_box_is_refused(client, bbox):
    assert client.get("/api/waterbodies", params={"bbox": bbox}).status_code == 422
    assert client.get("/api/shops", params={"bbox": bbox}).status_code == 422


@pytest.mark.parametrize("lat,lng", [(0, 0), (30, -140), (51.5, -0.12), (90, 0), (-33.9, 151.2)])
def test_a_catch_in_the_sea_or_abroad_is_refused(db_session, lat, lng):
    with pytest.raises(pins_svc.PinError) as e:
        pins_svc.locate(db_session, lat, lng)
    assert e.value.message == pins_svc.NOT_IN_THE_US


def test_a_catch_in_the_us_is_not_refused_for_that(db_session):
    # Austin; no water shapes imported in this database, so nothing else applies.
    assert pins_svc.locate(db_session, 30.27, -97.74) == (None, False)


@pytest.mark.parametrize("text", ["kill all jews", "GAS THE MUSLIMS", "hang all the blacks", "k1ll all j3ws"])
def test_hate_slogans_without_a_slur_are_refused(text):
    assert word_filter.blocked_word(text)


@pytest.mark.parametrize("text", ["kill all the bass", "hang the whites on a stringer", "the blacks were biting", "white bass power fishing", "kill the blacks and whites"])
def test_anglers_talking_about_fish_are_not(text):
    assert not word_filter.blocked_word(text)


@pytest.mark.parametrize("question", ["钓鱼", "낚시", "釣り", "hi"])
def test_two_characters_is_a_question(client, question):
    r = client.post("/api/ask", json={"question": question})
    assert r.status_code == 200 and r.json()["answer"]


@pytest.mark.parametrize("question", ["", " ", "     ", "\n\n\n", "a"])
def test_nothing_much_is_not_a_question(client, question):
    assert client.post("/api/ask", json={"question": question}).status_code == 422


def test_a_spanish_question_with_just_the_verb(client):
    r = client.post("/api/ask", json={"question": "¿dónde pesco?"})
    assert r.json()["trace"]["outcome"] != "off_topic"


def test_asking_about_a_lake_not_on_file_says_so(client):
    r = client.post("/api/ask", json={"question": "what fish are in Lake Doesnotexist"}).json()
    assert r["citations"] == [] and r["answer_source"] == "no_match"
    assert "Lake Doesnotexist" in r["answer"] and "on record" in r["answer"]
    assert r["trace"]["outcome"] == "no_match"  # and so it shows in the misses


def test_a_general_question_about_a_lake_still_gets_the_guides(client):
    r = client.post("/api/ask", json={"question": "what fish are in the lake"}).json()
    assert r["answer_source"] == "passages"
    r = client.post("/api/ask", json={"question": "what bass are in Lake Doesnotexist"}).json()
    assert r["answer_source"] == "passages"


def test_the_map_says_a_pin_abroad_needs_water_before_anyone_presses_save(client):
    where = client.get("/api/pins/where", params={"lat": 51.5, "lng": -0.12}).json()
    assert where["water_required"] is True and where["water"] is None


@pytest.mark.parametrize("species", ["\\", "%", "_", "a\\"])
def test_a_backslash_in_a_fish_name_finds_nothing(client, species):
    """On PostgreSQL a pattern ending in a backslash was a server error; SQLite
    let it through, so only production broke. Found running on real PostgreSQL."""
    r = client.get("/api/waterbodies", params={"species": species})
    assert r.status_code == 200 and r.json() == []
