"""What to buy (app/knowledge/gear.py)."""
from pydantic import BaseModel


class GearPhotoOut(BaseModel):
    """A Wikimedia Commons photo; the UI shows `author` and `license` with it."""

    url: str
    width: int
    height: int
    author: str
    license: str
    license_url: str | None
    file_page: str


class GearItemOut(BaseModel):
    id: str
    name: str
    category: str
    what: str
    tip: str
    topic: str | None  # the handbook topic (an anchor on /fish) that explains it
    fish: list[str]  # guide slugs
    first_kit: bool
    photo: GearPhotoOut | None


class GearCategoryOut(BaseModel):
    id: str
    label: str


class GearOut(BaseModel):
    categories: list[GearCategoryOut]
    items: list[GearItemOut]
    camera: bool = False  # the "what is this?" camera can answer (POST /api/gear/identify)


class GearCandidateOut(BaseModel):
    id: str  # an item of GET /api/gear
    name: str
    category: str
    probability: float  # its share of the photo's gear probability


class GearIdOut(BaseModel):
    """What the gear camera made of a photo (services/gear_id.py)."""

    available: bool  # false: the camera is switched off on this server
    model: str | None
    gear_probability: float | None  # how sure it is that the photo shows gear at all
    sure: bool  # the first candidate is named outright; otherwise compare them
    candidates: list[GearCandidateOut]  # likeliest first; empty when it isn't gear
    not_gear: str | None  # when it isn't gear, what it looks like most ("fish", "water", ...)
    message: str | None
