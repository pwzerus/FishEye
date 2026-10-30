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

import re
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
    # The age from which a licence is needed, for "do I need one?" in a line
    # (the start page, a lake's rules row); the handbook topic that says it
    # in full, with its exemptions; and the state's first-trip topic. Only
    # where those topics are written (angling_handbook.py, rule-license*).
    license_from_age: int | None = None
    license_topic: str | None = None
    first_trip_topic: str | None = None

    @property
    def covered(self) -> bool:
        """Does FishEye have reviewed rule passages for this state? Every
        state has its agency and pages on file (_AGENCIES); only these have
        rules written up, starting with the bait rules."""
        return bool(self.bait_rules)

    @property
    def agency_label(self) -> str:
        """What to call the people who set the rules, in a sentence."""
        return self.agency_short or f"{self.name}'s fish and wildlife agency"

    @property
    def agency_introduced(self) -> str:
        """The agency named in full once, for someone who has never heard of
        it: "ODWC (Oklahoma Department of Wildlife Conservation)"."""
        if self.agency and self.agency_short and self.agency_short != self.agency:
            return f"{self.agency_short} ({self.agency})"
        return self.agency or self.agency_label


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
        license_from_age=16,
        license_topic="rule-license-ca",
        first_trip_topic="start-first-trip-ca",
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
        license_from_age=16,
        license_topic="rule-license-ga",
        first_trip_topic="start-first-trip-ga",
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
        license_from_age=17,
        license_topic="rule-license",
        first_trip_topic="start-first-trip",
    ),
}

# Every other state's fish and wildlife agency, its fishing regulations page
# and its fishing licence page: (agency, short name, regulations, licences).
# Facts and links only (data-sourcing rule 3), so that "FishEye hasn't
# written this state's rules" can end in the state's own pages. Each link
# was opened on 2026-10-29 and showed that page; agencies move pages, so
# re-check them now and then (a 404 here sends people nowhere).
_AGENCIES: dict[str, tuple[str, str, str, str]] = {
    "AL": ("Alabama Department of Conservation and Natural Resources", "ADCNR",
           "https://www.outdooralabama.com/fishing/freshwater-fishing-creel-and-size-limits",
           "https://www.outdooralabama.com/license-information"),
    "AK": ("Alaska Department of Fish and Game", "ADF&G",
           "https://www.adfg.alaska.gov/index.cfm?adfg=fishregulations.main",
           "https://www.adfg.alaska.gov/index.cfm?adfg=license.main"),
    "AZ": ("Arizona Game and Fish Department", "AZGFD",
           "https://www.azgfd.com/fishing-2/licenses-and-regulations/",
           "https://www.azgfd.com/fishing-2/licenses-and-regulations/"),
    "AR": ("Arkansas Game and Fish Commission", "AGFC",
           "https://www.agfc.com/regulations/guidebooks/",
           "https://www.agfc.com/licenses/"),
    "CO": ("Colorado Parks and Wildlife", "CPW",
           "https://cpw.state.co.us/fishing",
           "https://cpw.state.co.us/activities/fishing/fishing-licenses-and-dates"),
    "CT": ("Connecticut Department of Energy and Environmental Protection", "CT DEEP",
           "https://portal.ct.gov/deep/fishing/regulations/fishing-regulations",
           "https://portal.ct.gov/deep/fishing/general-information/fisheries-licenses-and-permits"),
    "DE": ("Delaware Division of Fish and Wildlife", "DNREC",
           "https://dnrec.delaware.gov/fish-wildlife/fishing/regulations/",
           "https://dnrec.delaware.gov/fish-wildlife/licenses/"),
    "DC": ("District of Columbia Department of Energy and Environment", "DOEE",
           "https://doee.dc.gov/service/fishdc",
           "https://doee.dc.gov/service/get-fishing-license"),
    "FL": ("Florida Fish and Wildlife Conservation Commission", "FWC",
           "https://myfwc.com/fishing/freshwater/regulations/",
           "https://myfwc.com/license/recreational/"),
    "HI": ("Hawaii Department of Land and Natural Resources, Division of Aquatic Resources", "Hawaii DAR",
           "https://dlnr.hawaii.gov/dar/fishing/fishing-regulations/",
           "https://dlnr.hawaii.gov/dar/licenses-and-permits/freshwater-game-fishing-license/"),
    # Not opened: on 2026-10-29 every idfg.idaho.gov page showed a "web
    # services impacted" notice. Both are the addresses IDFG's own pages and
    # search results give; check them when the site is back.
    "ID": ("Idaho Department of Fish and Game", "IDFG",
           "https://idfg.idaho.gov/rules/fish",
           "https://idfg.idaho.gov/licenses"),
    "IL": ("Illinois Department of Natural Resources", "IDNR",
           "https://dnr.illinois.gov/doo/forms.html",
           "https://dnr.illinois.gov/lpr/fishinglicensesfees.html"),
    "IN": ("Indiana Department of Natural Resources", "Indiana DNR",
           "https://www.in.gov/dnr/fish-and-wildlife/fishing/fishing-guide-and-regulations/",
           "https://www.in.gov/dnr/fish-and-wildlife/licenses-and-permits/"),
    "IA": ("Iowa Department of Natural Resources", "Iowa DNR",
           "https://www.iowadnr.gov/things-do/fishing/regulations-laws",
           "https://www.iowadnr.gov/things-do/fishing/fishing-licenses"),
    "KS": ("Kansas Department of Wildlife and Parks", "KDWP",
           "https://www.ksoutdoors.gov/programs-services/law-enforcement/regulations-statutes/fishing-regulations",
           "https://www.ksoutdoors.gov/licenses-permits-fees/fishing-licenses-permit-fees"),
    "KY": ("Kentucky Department of Fish and Wildlife Resources", "KDFWR",
           "https://fw.ky.gov/FishBoatGuide/Pages/default.aspx",
           "https://fw.ky.gov/Licenses/Pages/default.aspx"),
    "LA": ("Louisiana Department of Wildlife and Fisheries", "LDWF",
           "https://www.wlf.louisiana.gov/page/recreational-freshwater-finfish-and-crawfish",
           "https://www.wlf.louisiana.gov/page/recreational-fishing-licenses-and-permits"),
    "ME": ("Maine Department of Inland Fisheries and Wildlife", "Maine IF&W",
           "https://www.maine.gov/ifw/fishing-boating/fishing/laws-rules/statewide-laws.html",
           "https://www.maine.gov/ifw/fishing-boating/fishing/laws-rules/license-requirements.html"),
    "MD": ("Maryland Department of Natural Resources", "Maryland DNR",
           "https://dnr.maryland.gov/fisheries/pages/regulations/index.aspx",
           "https://dnr.maryland.gov/pages/service_fishing_license.aspx"),
    "MA": ("Massachusetts Division of Fisheries and Wildlife", "MassWildlife",
           "https://www.mass.gov/info-details/freshwater-fishing-regulations",
           "https://www.mass.gov/how-to/buy-your-freshwater-fishing-license"),
    "MI": ("Michigan Department of Natural Resources", "Michigan DNR",
           "https://www.michigan.gov/dnr/things-to-do/fishing/fishing-regulations",
           "https://www.michigan.gov/dnr/things-to-do/fishing/license-info"),
    "MN": ("Minnesota Department of Natural Resources", "Minnesota DNR",
           "https://www.dnr.state.mn.us/regulations/fishing/index.html",
           "https://www.dnr.state.mn.us/licenses/fishing/index.html"),
    "MS": ("Mississippi Department of Wildlife, Fisheries, and Parks", "MDWFP",
           "https://www.mdwfp.com/enforcement-education/general-fishing-rules-regulations",
           "https://www.mdwfp.com/licenses-permits/fishing-license-requirements"),
    "MO": ("Missouri Department of Conservation", "MDC",
           "https://mdc.mo.gov/fishing/regulations",
           "https://mdc.mo.gov/permits"),
    "MT": ("Montana Fish, Wildlife & Parks", "Montana FWP",
           "https://fwp.mt.gov/fish/regulations",
           "https://fwp.mt.gov/buyandapply"),
    "NE": ("Nebraska Game and Parks Commission", "Nebraska Game and Parks",
           "https://outdoornebraska.gov/guides-maps/fishing-guides-reports/fishing-guide/",
           "https://outdoornebraska.gov/permits/fishing-permits/"),
    "NV": ("Nevada Department of Wildlife", "NDOW",
           "https://www.ndow.org/rules-regulations/",
           "https://www.ndow.org/apply-buy/fishing/"),
    "NH": ("New Hampshire Fish and Game Department", "NH Fish and Game",
           "https://www.wildlife.nh.gov/fishing-new-hampshire/fishing-seasons-nh",
           "https://www.wildlife.nh.gov/licenses-and-permits/nh-license-requirements"),
    "NJ": ("New Jersey Division of Fish and Wildlife", "NJ Fish & Wildlife",
           "https://dep.nj.gov/njfw/fishing/freshwater/regulations-and-permits/",
           "https://dep.nj.gov/njfw/fishing/freshwater/buy-a-license/"),
    "NM": ("New Mexico Department of Wildlife", "NMDOW",
           "https://wildlife.dgf.nm.gov/home/publications/",
           "https://wildlife.dgf.nm.gov/fishing/licenses-permits/"),
    "NY": ("New York State Department of Environmental Conservation", "NYSDEC",
           "https://dec.ny.gov/things-to-do/freshwater-fishing/regulations",
           "https://dec.ny.gov/regulatory/permits-licenses/sporting-and-use/sporting/fishing-license"),
    "NC": ("North Carolina Wildlife Resources Commission", "NCWRC",
           "https://www.ncwildlife.gov/hunt/fishing-hunting-trapping-regulations",
           "https://www.gooutdoorsnorthcarolina.com/"),
    "ND": ("North Dakota Game and Fish Department", "NDGF",
           "https://gf.nd.gov/regulations/fishing",
           "https://gf.nd.gov/fishing/licensing"),
    "OH": ("Ohio Department of Natural Resources, Division of Wildlife", "ODNR",
           "https://ohiodnr.gov/buy-and-apply/hunting-fishing-boating/fishing-resources/fishing-regulations",
           "https://ohiodnr.gov/buy-and-apply/hunting-fishing-boating/fishing-resources/fishing-licenses"),
    "OK": ("Oklahoma Department of Wildlife Conservation", "ODWC",
           "https://www.wildlifedepartment.com/fishing/regs",
           "https://www.wildlifedepartment.com/licensing"),
    "OR": ("Oregon Department of Fish and Wildlife", "ODFW",
           "https://myodfw.com/fishing/regulations",
           "https://myodfw.com/fishing/licensing-info"),
    "PA": ("Pennsylvania Fish and Boat Commission", "PFBC",
           "https://www.pa.gov/agencies/fishandboat/fishing/regulations",
           "https://www.pa.gov/agencies/fishandboat/fishing/buy-fishing-license-permit"),
    "RI": ("Rhode Island Department of Environmental Management", "RIDEM",
           "https://dem.ri.gov/natural-resources-bureau/fish-wildlife/rules-regulations/freshwater-sizes-and-limits",
           "https://dem.ri.gov/natural-resources-bureau/natural-resources-divisions/fish-wildlife/freshwater-fishing/licenses-0"),
    "SC": ("South Carolina Department of Natural Resources", "SCDNR",
           # No statewide rules page that loads; the fishing page links them.
           "https://www.dnr.sc.gov/fishing.html",
           "https://www.dnr.sc.gov/licenses/genlicense.html"),
    "SD": ("South Dakota Game, Fish and Parks", "SD GFP",
           "https://gfp.sd.gov/pages/regulations/",
           "https://gfp.sd.gov/hunt-fish-license/"),
    "TN": ("Tennessee Wildlife Resources Agency", "TWRA",
           "https://www.tn.gov/twra/fishing-regs.html",
           "https://www.tn.gov/twra/license-sales.html"),
    "UT": ("Utah Division of Wildlife Resources", "Utah DWR",
           "https://wildlife.utah.gov/guidebooks",
           "https://wildlife.utah.gov/licenses"),
    "VT": ("Vermont Fish and Wildlife Department", "Vermont Fish & Wildlife",
           "https://vtfishandwildlife.com/fish/fishing-regulations",
           "https://vtfishandwildlife.com/licenses-and-lotteries"),
    "VA": ("Virginia Department of Wildlife Resources", "Virginia DWR",
           "https://dwr.virginia.gov/fishing/regulations/",
           "https://dwr.virginia.gov/licenses/"),
    "WA": ("Washington Department of Fish and Wildlife", "WDFW",
           "https://wdfw.wa.gov/fishing/regulations",
           "https://wdfw.wa.gov/licenses/fishing"),
    "WV": ("West Virginia Division of Natural Resources", "WVDNR",
           "https://wvdnr.gov/fishing/fishing-regulations/",
           "https://wvdnr.gov/buy-a-license/"),
    "WI": ("Wisconsin Department of Natural Resources", "Wisconsin DNR",
           "https://dnr.wisconsin.gov/topic/fishing/regulations",
           "https://dnr.wisconsin.gov/topic/Fishing/outreach/FishingLicenses"),
    "WY": ("Wyoming Game and Fish Department", "WGFD",
           "https://wgfd.wyo.gov/regulations",
           "https://wgfd.wyo.gov/licenses-applications"),
}


def _uncovered(code: str, name: str) -> Jurisdiction:
    agency, short, limits_url, license_url = _AGENCIES.get(code, (None, None, None, None))
    return Jurisdiction(
        code=code, name=name, agency=agency, agency_short=short, limits_url=limits_url, license_url=license_url,
    )


JURISDICTIONS: dict[str, Jurisdiction] = {
    code: _COVERED.get(code) or _uncovered(code, name)
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
        f"(so far it has reviewed the rules for {covered_names()}). Rules for licenses, limits, bait and "
        f"boats differ from state to state, so check {j.agency_introduced} for the current ones. "
        "Everything about how to catch, handle and cook a fish works the same wherever you are."
    )


def other_state_answer_zh(state: str) -> str:
    """other_state_answer for a question asked in Chinese (docs/adr/0025)."""
    j = JURISDICTIONS[state]
    name = ZH_STATE_NAMES.get(state, j.name)
    agency = f" {j.agency_short} " if j.agency_short else f"{name}渔猎管理部门"
    if j.covered:
        return (
            f"FishEye 整理了{name}的部分钓鱼规定，但没有这个问题涉及的那一条。出钓前请查看{agency}的现行规定。"
            "怎么钓、怎么处理和烹饪鱼，在哪个州都一样。"
        )
    covered_zh = "、".join(ZH_STATE_NAMES.get(c.code, c.name) for c in covered())
    return (
        f"这是关于{name}钓鱼规定的问题，FishEye 还没有整理这个州的规定（目前只审核了{covered_zh}的规定）。"
        f"执照、尺寸和数量限制、饵料和船只的规定各州不同，请查看{agency}的现行规定。"
        "怎么钓、怎么处理和烹饪鱼，在哪个州都一样。"
    )


# --------------------------------------------------- a state named in a question

# Chinese names as people write them; the first of each is the one FishEye
# writes. 华盛顿 alone is left out: it usually means the city (DC).
_ZH_ALIASES: dict[str, tuple[str, ...]] = {
    "AL": ("阿拉巴马", "亚拉巴马"), "AK": ("阿拉斯加",), "AZ": ("亚利桑那",), "AR": ("阿肯色",),
    "CA": ("加州", "加利福尼亚"), "CO": ("科罗拉多",), "CT": ("康涅狄格",), "DE": ("特拉华",),
    "DC": ("华盛顿特区", "华盛顿哥伦比亚特区"), "FL": ("佛罗里达", "佛州"), "GA": ("佐治亚", "乔治亚"),
    "HI": ("夏威夷",), "ID": ("爱达荷",), "IL": ("伊利诺伊", "伊利诺斯"), "IN": ("印第安纳", "印地安那"),
    "IA": ("爱荷华", "艾奥瓦"), "KS": ("堪萨斯",), "KY": ("肯塔基",), "LA": ("路易斯安那",),
    "ME": ("缅因",), "MD": ("马里兰",), "MA": ("马萨诸塞", "麻省"), "MI": ("密歇根", "密西根"),
    "MN": ("明尼苏达", "明州"), "MS": ("密西西比",), "MO": ("密苏里",), "MT": ("蒙大拿",),
    "NE": ("内布拉斯加",), "NV": ("内华达",), "NH": ("新罕布什尔",), "NJ": ("新泽西",),
    "NM": ("新墨西哥",), "NY": ("纽约",), "NC": ("北卡罗来纳", "北卡"), "ND": ("北达科他", "北达科塔"),
    "OH": ("俄亥俄",), "OK": ("俄克拉荷马",), "OR": ("俄勒冈",), "PA": ("宾夕法尼亚", "宾州"),
    "RI": ("罗德岛",), "SC": ("南卡罗来纳", "南卡"), "SD": ("南达科他", "南达科塔"), "TN": ("田纳西",),
    "TX": ("得克萨斯", "德克萨斯", "得州", "德州"), "UT": ("犹他",), "VT": ("佛蒙特",),
    "VA": ("弗吉尼亚", "维吉尼亚"), "WA": ("华盛顿州",), "WV": ("西弗吉尼亚",), "WI": ("威斯康星", "威斯康辛"),
    "WY": ("怀俄明",),
}
ZH_STATE_NAMES: dict[str, str] = {code: names[0] for code, names in _ZH_ALIASES.items()}

# Fish, rigs and strains named after a state are not a place: a Texas rig is
# tied the same in Ohio. Kansas City is mostly in Missouri.
_NOT_A_PLACE = re.compile(
    r"\b(?:texas|carolina|alabama)\s+rigs?\b|\bkentucky\s+(?:spotted\s+)?bass\b"
    r"|\bflorida\s+(?:strain|bass|largemouth)\b|\bkansas\s+city\b|肯塔基鲈|佛罗里达鲈",
    re.I,
)

# Every way of writing a state, longest first, so "West Virginia" isn't
# read as Virginia, nor 西弗吉尼亚 as 弗吉尼亚.
_NAMES: list[tuple[str, str]] = sorted(
    [(name.lower(), code) for code, name in STATE_NAMES.items()]
    + [("washington, d.c.", "DC"), ("washington dc", "DC"), ("washington d.c.", "DC")]
    + [(alias, code) for code, aliases in _ZH_ALIASES.items() for alias in aliases],
    key=lambda nc: -len(nc[0]),
)
# English names whole words only ("Kansas" isn't in "Arkansas"); Chinese
# has no spaces to anchor on and needs none.
_NAME_RE = re.compile(
    "|".join(
        re.escape(n) if not n.isascii() else rf"\b{re.escape(n)}" + (r"\b" if n[-1].isalnum() else "")
        for n, _ in _NAMES
    ),
    re.I,
)
_CODE_OF = {n: c for n, c in _NAMES}


def state_in_question(text: str) -> str | None:
    """The state a question names ("do I need a license in Minnesota",
    "明尼苏达钓鱼要执照吗"), or None. Ask uses it ahead of the state picked on
    the page: someone asking about Minnesota wants Minnesota's rules
    wherever they are (the 2026-10-28 review found Minnesota questions
    answered with the rules of the three states FishEye covers). Two
    different states named: None, there is no one state to answer for."""
    found = {_CODE_OF[m.group(0).lower()] for m in _NAME_RE.finditer(_NOT_A_PLACE.sub(" ", text))}
    return found.pop() if len(found) == 1 else None
