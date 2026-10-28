"""County lookup from the Census outlines (services/counties.py)."""
from __future__ import annotations

import pytest

from app.data_import.census_counties import simplify
from app.services.counties import county_at, county_name


@pytest.mark.parametrize(
    "lat,lng,geoid,name",
    [
        (29.76, -95.37, "48201", "Harris County"),
        (30.0, -90.07, "22071", "Orleans Parish"),
        (61.2, -149.9, "02020", "Anchorage Municipality"),
        (21.3, -157.85, "15003", "Honolulu County"),
    ],
)
def test_points_land_in_their_county(lat, lng, geoid, name):
    c = county_at(lat, lng)
    assert (c.geoid, c.name) == (geoid, name)
    assert county_name(geoid) == name


def test_outside_the_us_there_is_no_county():
    assert county_at(0.0, 0.0) is None
    assert county_at(51.5, -0.12) is None  # London


def test_simplify_drops_points_on_a_straight_edge_but_keeps_corners():
    edge = [(0.0, 0.0)] + [(i / 10, 0.0) for i in range(1, 10)] + [(1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0)]
    assert simplify(edge) == [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0)]
