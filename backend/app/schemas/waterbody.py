from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str
    official_source_url: str
    # Whether any lake in this state is on file. The national map lights the
    # states where this is true and greys the rest as "coming soon". A State
    # row alone does not mean coverage: an import that found nothing still
    # creates one.
    has_waterbodies: bool = False


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


class ReportedSourceOut(BaseModel):
    name: str  # e.g. "Fishes of Texas (UT Austin)", "iNaturalist"
    records: int


class ReportedSpeciesOut(BaseModel):
    """A species someone has recorded at this lake (GBIF), summarised.
    Evidence that it has been found here, not an official confirmation:
    see docs/adr/0012-gbif-reported-species.md."""

    common_name: str
    records: int
    last_year: int | None
    sources: list[ReportedSourceOut]
    # A public page for the most recent record, so anyone can check it.
    latest_record_url: str | None
    # A single record from before 2000, or undated.
    weak: bool
    # Also on this lake's official (confirmed) species list.
    also_confirmed: bool


class WaterbodyListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    latitude: float
    longitude: float
    field_tested: bool
    public_access_status: str
    data_tier: str  # "verified" | "osm" — see models/waterbody.py
    water_type: str | None = None  # "lake" | "reservoir" | "pond"
    # Distinct species with outside records (GBIF) here; see ReportedSpeciesOut.
    reported_species_count: int = 0


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
    data_tier: str
    water_type: str | None = None
    access_points: list[AccessPointOut]
    species: list[SpeciesSummaryOut]
    reported_species: list[ReportedSpeciesOut] = []


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
