from pydantic import BaseModel

from app.schemas.species_guide import GuideSourceOut


class JurisdictionOut(BaseModel):
    """A state and who runs its fishing rules (knowledge/jurisdictions.py).
    `covered` says whether FishEye has reviewed rule passages for it; the
    links are null where it doesn't."""

    code: str
    name: str
    covered: bool
    agency: str | None
    agency_short: str | None
    limits_url: str | None
    license_url: str | None
    bait_rules: list[str]  # empty where FishEye hasn't written them
    bait_rules_sources: list[GuideSourceOut]
    # The bait rules contradict the guides' live-bait advice (California).
    bait_rules_on_every_bait_question: bool
    # Where FishEye wrote the state's licence topic: the age a licence is
    # needed from, that topic's id and the first-trip topic's (handbook ids).
    license_from_age: int | None = None
    license_topic: str | None = None
    first_trip_topic: str | None = None
