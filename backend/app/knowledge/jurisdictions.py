"""Which state's rules apply (docs/adr/0027).

How to catch a fish is the same everywhere; what you may keep, what licence
you need and what the law asks of your boat is not. The guides and the
handbook are written once, for every state, except the passages that state
a rule. Those carry a region (a state code, `REGION_ALL` for the rest) and
are shown only where they apply.

This registry is what the rest of the app asks "who runs the rules here?".
Texas is the one state with reviewed rule passages so far. Every other state
is listed so a person in it gets a straight answer — "FishEye hasn't
written this state's rules yet; they come from <name>'s fish and wildlife
agency" — instead of Texas's rules presented as theirs.

Adding a state is a data change here and in the passages it needs:
1. a `Jurisdiction` with the agency's name and the three pages below;
2. `region="<code>"` rule passages (handbook topics, bait rules), each
   citing that agency's own page;
nothing else in the code names a state.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.knowledge.species_guides import TPWD_LIMITS_URL

REGION_ALL = "all"

STATE_NAMES: dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
    "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}


@dataclass(frozen=True)
class Jurisdiction:
    code: str  # "TX"
    name: str  # "Texas"
    # None where no reviewed page is on file for the state yet.
    agency: str | None = None  # "Texas Parks and Wildlife Department"
    agency_short: str | None = None  # "TPWD"
    limits_url: str | None = None  # the agency's size and bag limits page
    license_url: str | None = None  # the agency's fishing licence page

    @property
    def covered(self) -> bool:
        """Does FishEye have reviewed rule passages for this state?"""
        return self.agency is not None

    @property
    def agency_label(self) -> str:
        """What to call the people who set the rules, in a sentence."""
        return self.agency_short or f"{self.name}'s fish and wildlife agency"


_COVERED: dict[str, Jurisdiction] = {
    "TX": Jurisdiction(
        code="TX",
        name="Texas",
        agency="Texas Parks and Wildlife Department",
        agency_short="TPWD",
        limits_url=TPWD_LIMITS_URL,
        license_url=(
            "https://tpwd.texas.gov/regulations/outdoor-annual/licenses/"
            "fishing-licenses-stamps-tags-packages/fishing-licenses-and-packages"
        ),
    ),
}

JURISDICTIONS: dict[str, Jurisdiction] = {
    code: _COVERED.get(code) or Jurisdiction(code=code, name=name)
    for code, name in sorted(STATE_NAMES.items(), key=lambda kv: kv[1])
}


def normalize(code: str | None) -> str | None:
    """"tx" -> "TX"; anything that isn't a state code -> None."""
    code = (code or "").strip().upper()
    return code if code in JURISDICTIONS else None


def get(code: str | None) -> Jurisdiction | None:
    key = normalize(code)
    return JURISDICTIONS[key] if key else None


def applies(region: str, state: str | None) -> bool:
    """May a passage with this region be shown to someone in `state`?

    With no state given, everything may: a rule passage names its state in
    its own text ("In Texas ..."), so it can't be mistaken for a general
    rule, and a person who hasn't said where they are still gets an answer.
    """
    return region == REGION_ALL or state is None or region == state


def other_state_answer(state: str) -> str:
    """What to say when the only passages that answer a question are another
    state's rules."""
    j = JURISDICTIONS[state]
    covered = ", ".join(c.name for c in JURISDICTIONS.values() if c.covered)
    return (
        f"That's a question about {j.name}'s fishing rules, and FishEye hasn't written those yet "
        f"(so far it has reviewed the rules for {covered}). Rules for licences, limits, bait and "
        f"boats differ from state to state, so check {j.agency_label} for the current ones. "
        "Everything about how to catch, handle and cook a fish works the same wherever you are."
    )
