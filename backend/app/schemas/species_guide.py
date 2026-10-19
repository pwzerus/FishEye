from pydantic import BaseModel


class GuideSourceOut(BaseModel):
    label: str
    url: str
    kind: str  # "agency" | "publication" | "guide"


class TackleSetupOut(BaseModel):
    name: str
    use_when: str
    method: str  # "lure" | "bait" | "either" — which of the two groups this setup belongs in
    rod: str
    reel: str
    line: str
    terminal: str
    sources: list[GuideSourceOut]


class SpeciesGuideOut(BaseModel):
    slug: str
    common_name: str
    scientific_name: str
    role: str  # "sport" | "forage"
    difficulty: str | None
    summary: str
    diet: str
    diet_type: str  # "carnivore" | "omnivore" | "filter_feeder"
    where_and_when: list[str]
    live_baits: list[str]
    lures: list[str]
    setups: list[TackleSetupOut]
    tips: list[str]
    identification: list[str]
    habitat: list[str]
    habits: list[str]
    why_these_baits: list[str]
    eating: list[str]
    how_to_get: list[str]
    bait_for: list[str]
    legal_notes: list[str]
    limits_url: str
    sources: list[GuideSourceOut]


class HandbookTopicOut(BaseModel):
    """One topic of the angler's handbook (app/knowledge/angling_handbook.py).
    `id` is the anchor on the fish guide page that answers cite."""

    id: str
    category: str
    category_label: str
    title: str
    body: list[str]
    sources: list[GuideSourceOut]


class SpeciesPhotoOut(BaseModel):
    """A real, freely licensed photo (services/species_photos.py). The UI
    must show `author` and `license` with it — that's the licence's term."""

    url: str
    width: int
    height: int
    author: str
    license: str
    license_url: str | None
    file_page: str
    source: str
