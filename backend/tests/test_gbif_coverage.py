"""Tests for the GBIF coverage experiment's report
(app/experiments/gbif_texas_coverage.py). Fetching and matching are shared
with the importer and tested in test_gbif_import.py."""
from __future__ import annotations

from app.data_import.osm_waterbody_import import Bounds, OsmLake
from app.experiments import gbif_texas_coverage as gbif


def _lake(ref, name, s, w, n, e, water_type="reservoir"):
    return OsmLake(ref, name, (s + n) / 2, (w + e) / 2, Bounds(s, w, n, e), water_type)


def _rec(key, lat, lng, species="Largemouth Bass", **extra):
    return {"key": key, "decimalLatitude": lat, "decimalLongitude": lng, "species": species, **extra}


# --- report -----------------------------------------------------------------


def test_report_counts_coverage_and_checks_agreement_with_tpwd():
    somerville_a = _lake("relation/1", "Lake Somerville", 30.25, -96.70, 30.40, -96.50)
    # The same reservoir mapped a second time under another word order.
    somerville_b = _lake("way/2", "Somerville Lake", 30.30, -96.60, 30.32, -96.58)
    pond = _lake("way/3", "Park Pond", 29.70, -95.40, 29.71, -95.39, water_type="pond")
    empty = _lake("way/4", "Empty Lake", 31.0, -97.0, 31.1, -96.9)
    lakes = [somerville_a, somerville_b, pond, empty]

    records = [
        _rec(1, 30.26, -96.65, "Largemouth Bass", year=2020, basisOfRecord="HUMAN_OBSERVATION"),
        _rec(2, 30.31, -96.59, "White Bass", year=2019, basisOfRecord="HUMAN_OBSERVATION"),
        _rec(3, 30.27, -96.66, "Striped Bass", year=1990, basisOfRecord="PRESERVED_SPECIMEN"),
        _rec(4, 29.705, -95.395, "Bluegill", year=2022, coordinateUncertaintyInMeters=10),
        _rec(5, 29.705, -95.395, "Bluegill", year=2022, coordinateUncertaintyInMeters=50_000),
        _rec(6, 35.0, -100.0, "Bluegill", year=2022),
    ]
    db_lakes = {"relation/1": ("Lake Somerville", "verified")}
    tpwd = [
        gbif.VerifiedLake(
            "Lake Somerville", 30.33, -96.59, frozenset({"Largemouth Bass", "White Bass", "Channel Catfish"})
        )
    ]

    report = gbif.build_report(lakes, records, db_lakes, tpwd)

    assert report["records"]["usable_coordinates"] == 5
    assert report["records"]["matched_to_a_lake"] == 4
    assert report["records"]["not_in_any_lake"] == 1
    assert report["coverage"]["lakes_with_any_record"] == 3
    assert report["coverage"]["by_water_type"]["pond"] == {"lakes": 1, "with_records": 1}
    assert report["coverage"]["verified_lakes_with_records"] == 1

    lake = report["tpwd_agreement"]["lakes"][0]
    # White Bass was recorded in the second OSM element and still counts.
    assert lake["both"] == ["Largemouth Bass", "White Bass"]
    assert lake["gbif_only"] == ["Striped Bass"]
    assert lake["tpwd_only"] == ["Channel Catfish"]
    assert report["tpwd_agreement"]["gbif_species_confirmed_by_tpwd"] == "2/3"
    assert report["tpwd_agreement"]["tpwd_species_found_in_gbif"] == "2/3"


def test_flood_control_structures_are_recognised_and_reported_separately():
    assert gbif.is_flood_control("Soil Conservation Service Site 13a Reservoir")
    assert not gbif.is_flood_control("Lake Conroe")
    scs = _lake("way/9", "Soil Conservation Service Site 4 Reservoir", 32.0, -97.0, 32.01, -96.99)
    real = _lake("way/8", "Lake Real", 31.0, -97.0, 31.1, -96.9)
    report = gbif.build_report([scs, real], [_rec(1, 32.005, -96.995, year=2020)], {}, [])
    assert report["coverage"]["flood_control_structures"] == {"lakes": 1, "with_records": 1}
    assert report["coverage"]["excluding_flood_control"] == {"lakes": 1, "with_records": 0}

