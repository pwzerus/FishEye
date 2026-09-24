from pydantic import BaseModel


class GuideSourceOut(BaseModel):
    label: str
    url: str
    kind: str  # "agency" | "publication" | "guide"


class TackleSetupOut(BaseModel):
    name: str
    use_when: str
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
    where_and_when: list[str]
    live_baits: list[str]
    lures: list[str]
    setups: list[TackleSetupOut]
    tips: list[str]
    identification: list[str]
    how_to_get: list[str]
    bait_for: list[str]
    legal_notes: list[str]
    limits_url: str
    sources: list[GuideSourceOut]
