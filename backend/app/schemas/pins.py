from datetime import date, datetime

from pydantic import BaseModel, Field


class PinAuthorOut(BaseModel):
    id: int
    display_name: str


class PinLakeOut(BaseModel):
    id: int
    name: str


class PinWaterOut(BaseModel):
    """The water a catch is on (ADR 0040)."""

    kind: str  # "lake" | "river"
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
    # Where this viewer sees the catch (ADR 0038): the exact spot for its
    # owner and admins, and for everyone when the angler shared it;
    # otherwise the public point, which `location_shown` names.
    latitude: float
    longitude: float
    location_shown: str  # "exact" | "lake" | "county" | "area"
    share_exact: bool
    # What everyone else sees: "exact" when shared, else lake/county/area.
    public_place: str
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
    # The lake or river it's on; None for a pin saved before ADR 0040 that
    # is on neither.
    water: PinWaterOut | None = None
    # One of its photos was taken within 300 m of the spot, by the photo's
    # own GPS (services/pins.update_photo_at_spot).
    photo_at_spot: bool = False
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
    share_exact: bool | None = None
    # A new spot: both or neither. It must be on water, like a new pin's.
    latitude: float | None = None
    longitude: float | None = None
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


class WhereWaterOut(BaseModel):
    kind: str  # "lake" | "river"
    id: int
    name: str
    distance_m: float  # 0: on the water


class WhereOut(BaseModel):
    state_code: str | None
    state_name: str | None
    county_geoid: str | None
    county_name: str | None
    # The water a catch here would be on (ADR 0040), and whether this
    # state holds catches to that: when True and `water` is None, a pin
    # can't be saved here.
    water: WhereWaterOut | None = None
    water_required: bool = False


class WaterGroupOut(BaseModel):
    """Other people's catches on one water, for the map (ADR 0040): a lake,
    a river within one county, or (pins saved before, on no water) one
    public point."""

    kind: str  # "lake" | "river" | "place"
    id: int | None  # the lake's or river's id
    # The newest catch's state and county: where the catches page lists
    # them (it browses by county). A river's group is one county's.
    state_code: str | None
    county_geoid: str | None
    name: str | None
    county_name: str | None
    latitude: float
    longitude: float
    count: int
    latest_at: datetime
    species: list[str]  # the most caught first, up to three
    thumb_url: str | None
