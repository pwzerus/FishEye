from pydantic import BaseModel


class GeocodeResultOut(BaseModel):
    query: str
    display_name: str
    latitude: float
    longitude: float


class PlaceSuggestionOut(BaseModel):
    """A place offered while typing (services/place_suggest.py): its own
    point, so choosing it needs no geocoding."""

    label: str
    name: str
    state: str
    kind: str  # place, county, town (New England) or zip
    latitude: float
    longitude: float
