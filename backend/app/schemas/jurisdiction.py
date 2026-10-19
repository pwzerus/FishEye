from pydantic import BaseModel


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
