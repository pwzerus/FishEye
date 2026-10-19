"""GET /api/jurisdictions — the states, and who runs the fishing rules in each.

The frontend asks this instead of naming an agency itself, so adding a state
is a change to knowledge/jurisdictions.py and nothing else (docs/adr/0027)."""
from fastapi import APIRouter

from app.knowledge.jurisdictions import JURISDICTIONS
from app.schemas.jurisdiction import JurisdictionOut

router = APIRouter(prefix="/jurisdictions", tags=["jurisdictions"])


@router.get("", response_model=list[JurisdictionOut])
def list_jurisdictions() -> list[JurisdictionOut]:
    """Covered states first, then the rest by name."""
    ordered = sorted(JURISDICTIONS.values(), key=lambda j: (not j.covered, j.name))
    return [
        JurisdictionOut(
            code=j.code,
            name=j.name,
            covered=j.covered,
            agency=j.agency,
            agency_short=j.agency_short,
            limits_url=j.limits_url,
            license_url=j.license_url,
        )
        for j in ordered
    ]
