from datetime import date, datetime

from pydantic import BaseModel, Field


class PinAuthorOut(BaseModel):
    id: int
    display_name: str


class PinLakeOut(BaseModel):
    id: int
    name: str


class PinPhotoOut(BaseModel):
    id: int
    url: str
    thumb_url: str
    width: int
    height: int


class PinSummaryOut(BaseModel):
    id: int
    latitude: float
    longitude: float
    title: str
    species_slug: str | None
    species_label: str | None
    # The photo check (services/fish_id.py): "confirmed", "group" (a
    # look-alike; `species_check_label` says which kind, e.g. "a black
    # bass"), or None (no species named, or not checked).
    species_check: str | None
    species_check_label: str | None
    caught_on: date | None
    created_at: datetime
    visibility: str  # "public" | "private"
    status: str  # "published" | "hidden" | "removed"
    status_reason: str | None
    author: PinAuthorOut
    lake: PinLakeOut | None
    # Where it is, for "Harris County, TX" (services/counties.py).
    state_code: str | None = None
    county_geoid: str | None = None
    county_name: str | None = None
    photo_count: int
    thumb_url: str | None
    is_mine: bool


class PinDetailOut(PinSummaryOut):
    note: str | None
    photos: list[PinPhotoOut]
    can_edit: bool
    can_report: bool
    reported_by_me: bool


class PinUpdateIn(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=2000)
    species_slug: str | None = None
    species_other: str | None = Field(default=None, max_length=120)
    caught_on: date | None = None
    visibility: str | None = None
    # Explicit clears, since None means "unchanged" for the fields above.
    clear_note: bool = False
    clear_species: bool = False
    clear_caught_on: bool = False


class ReportIn(BaseModel):
    reason: str
    detail: str | None = Field(default=None, max_length=1000)


class ReportOut(BaseModel):
    received: bool
    pin_hidden: bool


class FishCandidateOut(BaseModel):
    slug: str
    label: str
    probability: float
    in_guides: bool  # one of the species a catch can name


class FishVerdictOut(BaseModel):
    status: str  # confirmed | group | mismatch | other_fish | no_fish | unsure
    accepted: bool
    detected: str | None
    detected_label: str | None
    detected_in_guides: bool
    message: str


class FishIdOut(BaseModel):
    available: bool  # False: the check is off here (FISH_ID=off)
    model: str | None
    fish_probability: float | None
    candidates: list[FishCandidateOut]  # the likeliest fish first
    verdict: FishVerdictOut | None  # only when a species was given


class PinOptionsOut(BaseModel):
    species: list[dict[str, str]]  # [{slug, label}]
    report_reasons: list[dict[str, str]]  # [{id, label}]
    max_photos: int
    max_photo_mb: int


class PlaceOut(BaseModel):
    # A state code, a county GEOID, or a lake id ("0": not at a mapped lake).
    id: str
    name: str
    count: int


class PlacesOut(BaseModel):
    level: str  # "state" | "county" | "lake": what `places` lists
    places: list[PlaceOut]
    # The names of the state and county asked for, for the breadcrumb.
    state_name: str | None = None
    county_name: str | None = None


class WhereOut(BaseModel):
    state_code: str | None
    state_name: str | None
    county_geoid: str | None
    county_name: str | None
