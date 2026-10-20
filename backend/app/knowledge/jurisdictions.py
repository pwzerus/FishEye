"""Which state's rules apply (docs/adr/0027).

How to catch a fish is the same everywhere; what you may keep, what licence
you need and what the law asks of your boat is not. The guides and the
handbook are written once, for every state, except the passages that state
a rule. Those carry a region (a state code, `REGION_ALL` for the rest) and
are shown only where they apply.

This registry is what the rest of the app asks "who runs the rules here?".
Texas, Georgia and California have reviewed rule passages so far. Every other state
is listed so a person in it gets a straight answer — "FishEye hasn't
written this state's rules yet; they come from <name>'s fish and wildlife
agency" — instead of Texas's rules presented as theirs.

Adding a state is a data change here and in the passages it needs
(Georgia, docs/adr/0028, is the worked example):
1. a `Jurisdiction` with the agency's name, its limits and licence pages,
   and its bait rules with their sources;
2. `region="<code>"` handbook topics (licence, life jackets, invasive
   species, a first trip), each citing that agency's own pages;
nothing else in the code names a state.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.knowledge.species_guides import BAIT_RULES, TPWD_LIMITS_URL

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
    # What may go on the hook and where, paraphrased closely from the
    # agency, with the sources it came from. One retrievable passage per
    # state (services/rag/chunking.py) and the bait-rules card on the guide.
    bait_rules: tuple[str, ...] = ()
    bait_rules_source_ids: tuple[str, ...] = ()
    # True where the bait rules contradict the guides' general advice (the
    # guides recommend live minnows; California forbids fish as bait in most
    # inland waters). Then every bait question in that state shows the rules,
    # whatever they rank (services/rag/ask.py, docs/adr/0030).
    bait_rules_on_every_bait_question: bool = False

    @property
    def covered(self) -> bool:
        """Does FishEye have reviewed rule passages for this state?"""
        return self.agency is not None

    @property
    def agency_label(self) -> str:
        """What to call the people who set the rules, in a sentence."""
        return self.agency_short or f"{self.name}'s fish and wildlife agency"


# Georgia's, from the regulations guide's fishing-methods and general pages
# and the shared-waters agreement with Alabama (garegs-*). Conditions kept;
# no lengths or counts, which change and vary by water (as for Texas).
GEORGIA_BAIT_RULES = (
    "Game fish may be used as live bait where live bait is legal, if they were caught "
    "legally, and they count toward your daily creel and possession limits.",
    "Threadfin shad, gizzard shad and blueback herring may be taken for bait with a dip net or "
    "cast net, but cast nets may not be used in state park lakes or on any Public Fishing Area.",
    "Small nongame fish may be taken for bait with a minnow seine or trap of the legal size; "
    "every other fish caught in it must go back unharmed straight away. Seines and traps are "
    "not allowed in designated trout waters and some listed rivers.",
    "Bait species should never be moved from one waterway to another.",
    "On the Chattahoochee lakes Georgia shares with Alabama, such as West Point and Walter F. "
    "George, it is illegal to have or fish with live blueback herring.",
)

# California's, from CDFW's 2026 freshwater booklet (Title 14, sections
# 1.63 and 4.00-4.30). The important difference from Texas and Georgia: in
# most inland waters, fish may not be used as bait at all. The per-district
# species lists are long and change; the card says so and links the booklet.
CALIFORNIA_BAIT_RULES = (
    "In most of California's inland waters, live or dead fin fish \u2014 minnows, shiners, shad "
    "and other fish \u2014 may not be used as bait. "
    "Each district (Southern, Colorado River, Valley and South Central, North Central, Sierra "
    "and North Coast) allows only the species and waters its rules list.",
    "Where a district allows a fish such as threadfin shad or Mississippi silverside as live "
    "bait, it may be used only in the water where it was caught: live fish may not be carried "
    "away from the water where they were taken.",
    "Dead ocean fish may be used as bait statewide, except where special rules say otherwise.",
    "Worms, insects, crayfish and other legally taken invertebrates, and frogs, may be used as "
    "bait; salamanders may not. Crayfish may not be used as bait in the Pit River and its "
    "tributaries.",
    "No trout may be kept alive in a container on or attached to a boat.",
)

_COVERED: dict[str, Jurisdiction] = {
    "CA": Jurisdiction(
        code="CA",
        name="California",
        agency="California Department of Fish and Wildlife",
        agency_short="CDFW",
        # Limits are set water by water; CDFW's interactive map shows them.
        limits_url="https://apps.wildlife.ca.gov/sportfishingregs/",
        license_url="https://wildlife.ca.gov/Licensing/Fishing",
        bait_rules=CALIFORNIA_BAIT_RULES,
        bait_rules_source_ids=("cdfw-regs-2026",),
        bait_rules_on_every_bait_question=True,
    ),
    "GA": Jurisdiction(
        code="GA",
        name="Georgia",
        agency="Georgia Department of Natural Resources, Wildlife Resources Division",
        agency_short="Georgia WRD",
        limits_url="https://www.eregulations.com/georgia/fishing/game-species-daily-limits",
        license_url="https://georgiawildlife.com/licenses-permits-passes/choose",
        bait_rules=GEORGIA_BAIT_RULES,
        bait_rules_source_ids=("garegs-methods", "garegs-general", "garegs-bordering"),
    ),
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
        bait_rules=BAIT_RULES,
        bait_rules_source_ids=("tpwd-regs-general",),
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


def covered() -> list[Jurisdiction]:
    return [c for c in JURISDICTIONS.values() if c.covered]


def covered_names() -> str:
    """"Georgia and Texas" — for sentences."""
    names = [c.name for c in covered()]
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def bait_rules_section(code: str) -> str:
    """The passage section (and page anchor) for a state's bait rules.
    Texas keeps the "bait_rules" it had before there were two states, which
    links and eval cases already point at."""
    return "bait_rules" if code == "TX" else f"bait_rules-{code.lower()}"


def other_state_answer(state: str) -> str:
    """What to say when the only passages that answer a question are another
    state's rules."""
    j = JURISDICTIONS[state]
    if j.covered:
        return (
            f"FishEye has written some of {j.name}'s fishing rules, but not the one this question "
            f"is about. Check {j.agency_label} for the current rules before you fish. Everything about "
            "how to catch, handle and cook a fish works the same wherever you are."
        )
    return (
        f"That's a question about {j.name}'s fishing rules, and FishEye hasn't written those yet "
        f"(so far it has reviewed the rules for {covered_names()}). Rules for licences, limits, bait and "
        f"boats differ from state to state, so check {j.agency_label} for the current ones. "
        "Everything about how to catch, handle and cook a fish works the same wherever you are."
    )
