"""Which GBIF photos the fish recognizer is measured and fitted on (no network)."""
from app.cli.fish_id_photos import LOOKALIKES, pick_photos, targets
from app.services.fish_id_classes import CLASSES, OTHER_FISH, SAME_FISH

CC_BY = "http://creativecommons.org/licenses/by/4.0/"
CC_BY_NC = "http://creativecommons.org/licenses/by-nc/4.0/"
CC0 = "http://creativecommons.org/publicdomain/zero/1.0/"


def occ(key, obs, *media):
    return {"key": key, "occurrenceID": f"https://www.inaturalist.org/observations/{obs}", "media": list(media)}


def photo(n, licence, creator="Ann"):
    return {"type": "StillImage", "license": licence, "creator": creator,
            "identifier": f"https://inaturalist-open-data.s3.amazonaws.com/photos/{n}/original.jpg"}


def test_only_openly_licensed_photos_one_per_observation_in_medium_size():
    results = [
        occ(1, 100, photo(1, CC_BY_NC), photo(2, CC_BY)),  # the NC photo is skipped, the CC BY one taken
        occ(2, 100, photo(3, CC0)),  # same observation again: skipped
        occ(3, 101, photo(4, CC_BY_NC)),  # nothing open: skipped
        occ(4, 102, photo(5, CC0, creator="Bo"), photo(6, CC0)),
    ]
    picked = pick_photos(results, want=10, seen=set())
    assert [p["gbif_id"] for p in picked] == [1, 4]
    assert picked[0]["url"].endswith("/photos/2/medium.jpg") and picked[0]["licence"] == "CC BY 4.0"
    assert picked[1]["licence"] == "CC0 1.0" and picked[1]["creator"] == "Bo"


def test_stops_at_what_is_wanted_and_skips_observations_already_held():
    results = [occ(i, 200 + i, photo(i, CC_BY)) for i in range(5)]
    assert len(pick_photos(results, want=2, seen=set())) == 2
    held = {"https://www.inaturalist.org/observations/200"}
    assert [p["gbif_id"] for p in pick_photos(results, want=2, seen=held)] == [1, 2]


def test_photos_cover_every_fish_class_the_recognizer_knows():
    # A steelhead has no species of its own: its photos come from Commons
    # (fish_id_commons.py), not from a species search.
    fish = {c.slug for c in CLASSES if c.kind != "not_fish"} - set(SAME_FISH)
    assert set(targets()) == fish
    assert set(LOOKALIKES) == {c.slug for c in CLASSES if c.kind == OTHER_FISH} - set(SAME_FISH)


def test_commons_photos_are_open_licences_only():
    from app.cli.fish_id_commons import licence_ok

    for ok in ("Public domain", "CC0", "CC BY 2.0", "CC BY 4.0", "No restrictions"):
        assert licence_ok(ok), ok
    for refused in ("CC BY-SA 4.0", "CC BY-NC 2.0", "CC BY-ND 3.0", "GFDL", "", None):
        assert not licence_ok(refused), refused
