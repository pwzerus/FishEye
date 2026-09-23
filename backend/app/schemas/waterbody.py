from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str
    official_source_url: str


class AccessPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    latitude: float
    longitude: float
    access_type: str
    public_status: str
    parking: bool


class SpeciesSummaryOut(BaseModel):
    """Species as seen from a waterbody listing — confidence-qualified,
    never a bare species name (PRD §4.2: don't equate statewide species
    lists with what's actually confirmed in a given lake)."""

    model_config = ConfigDict(from_attributes=True)
    common_name: str
    difficulty: str
    confidence: str
    evidence: str
    source_url: str
    observed_at: datetime


class WaterbodyListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    latitude: float
    longitude: float
    field_tested: bool
    public_access_status: str


class WaterbodyDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    latitude: float
    longitude: float
    access_summary: str
    source_url: str
    source_updated_at: datetime
    field_tested: bool
    public_access_status: str
    access_points: list[AccessPointOut]
    species: list[SpeciesSummaryOut]


class SpeciesConditionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    season: str
    temperature_range: str
    weather_preferences: str
    habitat_rules: str


class SpeciesDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    common_name: str
    scientific_name: str
    difficulty: str
    profile: str
    conditions: list[SpeciesConditionOut]
