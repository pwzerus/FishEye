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


class EvidenceItemOut(BaseModel):
    """One official fact that the species is here (models.SpeciesEvidence):
    FishEye's own sentence and a link to the source."""

    evidence: str
    source_url: str
    kind: str  # stocking | stocking_plan | survey | record
    year: int | None = None
    publisher: str | None = None


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
    # Every official fact behind this species, newest first. Empty for links
    # written before species_evidence existed (TPWD, Georgia WRD), whose one
    # sentence and link are `evidence` and `source_url`.
    evidence_items: list[EvidenceItemOut] = []


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


class AgencyRatingOut(BaseModel):
    label: str  # the agency's own species-group label
    rating: str  # Poor | Fair | Good | Excellent


class AgencyProfileOut(BaseModel):
    """What the state agency publishes about this lake, as it wrote it
    (models.waterbody.AgencyLakeProfile)."""

    model_config = ConfigDict(from_attributes=True)
    agency: str
    agency_name: str
    page_url: str
    access_page_url: str | None = None
    survey_report_url: str | None = None
    survey_year: int | None = None
    location: str | None = None
    surface_acres: int | None = None
    max_depth_ft: int | None = None
    impounded: str | None = None
    predominant_species: list[str] = []
    ratings: list[AgencyRatingOut] = []
    # How the lake was put on the map; "ramps" means at its boat ramps, with
    # no outline (see tpwd_statewide_import.py).
    placement: str


class DatasetSourceOut(BaseModel):
    """A dataset behind this lake's facts, with the credit it asks for
    (data-sourcing rule 7)."""

    title: str
    publisher: str
    licence: str | None = None
    citation: str | None = None
    url: str


class FishAttractorOut(BaseModel):
    """A fish attractor the state agency placed here (models.waterbody.FishAttractor)."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    latitude: float
    longitude: float
    attractor_type: str
    units: int | None = None
    depth_ft: float | None = None
    placed_year: int | None = None
    source: str


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
    agency_profile: AgencyProfileOut | None = None
    fish_attractors: list[FishAttractorOut] = []
    # The lake's name on the state agency's map, when it differs from `name`.
    official_name: str | None = None
    # PAD-US: the lake's centre is on land open to the public ("open") or
    # open with limits ("restricted"), and which land that is.
    public_land: str | None = None
    public_land_name: str | None = None
    public_land_manager: str | None = None
    # "Data: <agency>" for facts from a state agency (shown with the facts).
    data_credit: str | None = None
    sources: list[DatasetSourceOut] = []


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
