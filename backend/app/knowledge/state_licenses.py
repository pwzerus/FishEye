"""Who needs a fishing license, for the states beyond the three written in full.

Read 2026-11-01 from each agency's own page, or its eRegulations guide where
the agency's page couldn't be read (docs/data-sources.md), and put in our own
words: the age a license starts at, the main exemptions, and any stamp a trout
angler needs. No fees and no dated free-fishing days, which go stale; a rule
for which days are free stays. Each becomes one handbook topic shown only in
its state (angling_handbook.py) and one source (species_guides.py).

Checked again 2026-11-06 against the same pages (docs/data-sources.md); where
an agency page carries no age (Alaska's main page, Oregon's, Utah's...), the
source is now the page that states it. Massachusetts, Minnesota, Nebraska,
New Hampshire and New Jersey were added then, so every state and DC has one.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StateLicense:
    resident_from: int | None  # the age a resident needs one from; None: the page gives none
    nonresident_from: int | None
    url: str
    notes: tuple[str, ...]


_ER = "https://www.eregulations.com"

STATE_LICENSES: dict[str, StateLicense] = {
    "AL": StateLicense(16, 16, f"{_ER}/alabama/fishing/fishing-licenses-fees", (
        "Residents under 16 or 65 and older are exempt from the freshwater license, and residents fishing with ordinary hook and line from the bank in their home county don't need one.",
        "On Free Fishing Day each June no license is needed on public waters, though state public fishing lakes still need a permit.",
    )),
    "AK": StateLicense(18, 16, "https://www.adfg.alaska.gov/index.cfm?adfg=sportlicense.main", (
        "Residents 60 and older and resident disabled veterans don't need a license if they hold an ADF&G ID card.",
        "King salmon also need a King Salmon Stamp, except for residents under 18 and non-residents under 16.",
    )),
    "AZ": StateLicense(10, 10, f"{_ER}/arizona/fishing/license-fee-structure", (
        "Blind residents, and anyone on private waters with the owner's permission, are exempt.",
        "No license is needed on the first Saturday of National Fishing and Boating Week. The license covers trout, with no separate stamp.",
    )),
    "AR": StateLicense(16, 16, f"{_ER}/arkansas/fishing/fishing-license-descriptions-and-fees", (
        "Licensed put-and-take pay lakes are exempt. A Trout Permit is needed on certain waters and to keep trout.",
    )),
    "CO": StateLicense(16, 16, "https://cpw.state.co.us/activities/fishing/fishing-licenses-and-dates", (
        "Active-duty residents on leave are exempt for up to 30 days a year. Anglers 18 to 64 also need a Habitat Stamp with their license.",
    )),
    "CT": StateLicense(16, 16, "https://portal.ct.gov/deep/fishing/general-information/fisheries-licenses-and-permits", (
        "Residents 65 and older get theirs free, but still need one. Trout and salmon anglers may need a Trout and Salmon Stamp.",
    )),
    "DE": StateLicense(16, 16, "https://dnrec.delaware.gov/fish-wildlife/licenses/", (
        "Residents 65 and older and veterans with a service-connected disability of 60% or more are exempt.",
        "Trout anglers need a Delaware Trout Stamp, except residents 65 and older.",
    )),
    "DC": StateLicense(16, 16, "https://doee.dc.gov/service/get-fishing-license", (
        "People 65 and older are also exempt.",
    )),
    "FL": StateLicense(16, 16, "https://www.myfwc.com/license/recreational/do-i-need-one/", (
        "Residents 65 and older, certified disabled residents, and military on leave for up to 30 days are exempt, as are private ponds of 20 acres or less.",
        "Freshwater is license-free on the first weekend of April and the second weekend of June.",
    )),
    "HI": StateLicense(None, None, "https://dlnr.hawaii.gov/dar/licenses-and-permits/freshwater-game-fishing-license/", (
        "Anyone taking introduced freshwater sport fish (bass, trout, tilapia and the like) needs a freshwater game fishing license. Minors need one from 9, at a minors' rate up to 15.",
        "Visitors can buy a 7-day or 30-day tourist license, and seniors 65 and older get theirs free.",
    )),
    "ID": StateLicense(14, 14, f"{_ER}/idaho/fishing/licenses-tags-and-permits", (
        "A non-resident under 14 needs no license only when with an Idaho license holder. There is no trout stamp.",
    )),
    "IL": StateLicense(16, 16, f"{_ER}/illinois/fishing/fishing-licenses", (
        "Disabled or blind residents with proof, landowners on their own waters and active-duty military on leave are exempt.",
        "Trout outside Lake Michigan need an Inland Trout Stamp; Lake Michigan has its own salmon stamp.",
    )),
    "IN": StateLicense(18, 18, f"{_ER}/indiana/fishing/fishing-licenses-fees", (
        "Blind or developmentally disabled residents, residents on military leave, and private ponds with no link to public water are exempt.",
        "Trout and salmon in public waters need a Trout/Salmon Stamp as well.",
    )),
    "IA": StateLicense(16, 16, "https://www.iowadnr.gov/things-do/fishing/fishing-licenses", (
        "Active-duty military on authorized leave are exempt. There's no exemption for seniors. Trout need a Trout Fee, and under-16s may need it too.",
    )),
    "KS": StateLicense(16, 16, f"{_ER}/kansas/fishing/licenses-permits-and-fees", (
        "The resident license is for ages 16 through 74. Non-residents are exempt on private ponds not leased for public fishing. Trout need a Trout Permit.",
    )),
    "KY": StateLicense(16, 16, "https://fw.ky.gov/Licenses/Pages/License-and-Permit-Descriptions.aspx", (
        "Trout anglers need a Trout Permit, which Sportsman's licenses include.",
    )),
    "LA": StateLicense(18, 18, f"{_ER}/louisiana/fishing/license-information", (
        "Louisiana and Texas honor each other's licenses on their border waters. A Free Fishing Weekend is held each June.",
    )),
    "ME": StateLicense(16, 16, f"{_ER}/maine/fishing/license-requirements-and-fees", (
        "There's no general exemption beyond that age, though blind residents and veterans with a disability of 50% or more can get one free.",
    )),
    "MD": StateLicense(16, 16, "https://dnr.maryland.gov/pages/service_fishing_license.aspx", (
        "Residents on military leave and anglers on charters or commercial piers are exempt.",
        "Trout in non-tidal waters need a Trout Stamp from 16. The first two Saturdays in June and July 4 are license-free.",
    )),
    "MI": StateLicense(17, 17, f"{_ER}/michigan/fishing/fishing-license-information", (
        "Active-duty military and fully disabled veterans can get one free. At 65 and older there's a senior license, not an exemption.",
    )),
    "MS": StateLicense(16, 16, "https://www.mdwfp.com/licenses-permits/fishing-license-requirements", (
        "The resident license is for ages 16 through 64. Privately owned ponds and streams are exempt, as are some disabled residents.",
    )),
    "MO": StateLicense(16, 16, "https://mdc.mo.gov/permits/permit-exemptions", (
        "Residents 65 and older are exempt, except for trout. So are veterans with a disability of 60% or more, and landowners whose land surrounds the water.",
        "Trout need a Trout Permit, or a daily tag in trout parks. The weekend after the first Monday in June is free.",
    )),
    "MA": StateLicense(15, 15, "https://www.mass.gov/how-to/buy-your-freshwater-fishing-license", (
        "Residents 15 to 17 and 70 and older still need one, but get it free.",
    )),
    "MN": StateLicense(16, 16, f"{_ER}/minnesota/fishing/license-guide", (
        "A non-resident under 16 needs no license only if a parent or guardian is licensed. Residents 90 and older are exempt.",
        "Minnesota holds free fishing weekends, such as Take a Kid Fishing Weekend in June.",
    )),
    "MT": StateLicense(12, 12, "https://fwp.mt.gov/buyandapply/fishinglicenses", (
        "Anglers also need an AIS Prevention Pass.",
    )),
    "NE": StateLicense(16, 16, "https://outdoornebraska.gov/permits/fishing-permits/", (
        "The fishing permit includes the Aquatic Habitat Stamp that Nebraska requires.",
    )),
    "NH": StateLicense(16, 16, "https://www.wildlife.nh.gov/licenses-and-permits/nh-license-requirements", (
        "Residents 68 and older can buy a discounted senior license, and residents born in 1947 or earlier can get a free permanent one.",
    )),
    "NJ": StateLicense(16, 16, "https://dep.nj.gov/njfw/fishing/freshwater/buy-a-license/", (
        "The license is needed even on privately owned waters. Trout and salmon need a Trout Stamp as well.",
    )),
    "NV": StateLicense(12, 12, "https://www.ndow.org/apply-buy/fishing/", (
        "Discounted licenses exist for residents 65 and older, disabled residents and disabled veterans.",
    )),
    "NM": StateLicense(12, 12, "https://wildlife.dgf.nm.gov/fishing/licenses-permits/", (
        "Tribal reservations and private Class-A lakes are exempt. Residents 70 and older and 100%-disabled resident veterans can get a free license.",
        "A Habitat Stamp is needed on Forest Service and BLM land from 12.",
    )),
    "NY": StateLicense(16, 16, "https://dec.ny.gov/regulatory/permits-licenses/sporting-and-use/sporting/fishing-license", (
        "Licensed preserves, free learn-to-fish clinics and farm landowners are exempt. New York also sets Free Fishing Days.",
    )),
    "NC": StateLicense(16, 16, f"{_ER}/northcarolina/hunting-fishing/fishing-licenses/", (
        "Private ponds are exempt. Designated trout waters need a Mountain Heritage Trout license.",
    )),
    "ND": StateLicense(16, 16, "https://gf.nd.gov/fishing/licensing", (
        "A non-resident under 16 must be with a licensed adult. Residents have four free days a year, not for paddlefish.",
    )),
    "OH": StateLicense(16, 16, f"{_ER}/ohio/fishing/licenses-fees", (
        "Private ponds with no fish moving in from public water, active-duty military on leave, and landowners on their own land are exempt.",
    )),
    "OK": StateLicense(18, 18, "https://www.wildlifedepartment.com/licensing/regs/license-exemptions", (
        "Resident private-pond owners and tenants with their families, and resident veterans with a disability of 60% or more, are exempt.",
    )),
    "OR": StateLicense(12, 12, f"{_ER}/oregon/fishing/license-information", (
        "Resident landowners on their own land are exempt, but not for salmon, steelhead, sturgeon or halibut. Anglers of any age need a Combined Angling Tag for those four.",
    )),
    "PA": StateLicense(16, 16, "https://www.pa.gov/agencies/fishandboat/fishing/buy-fishing-license-permit", (
        "Trout need a Trout Permit from 16, and Lake Erie has its own permit. Seniors get a discount, not an exemption.",
    )),
    "RI": StateLicense(15, 15, f"{_ER}/rhodeisland/fishing/freshwater/license-information", (
        "Blind people and landowners on their own property are exempt. Residents over 65 can get a free permanent license.",
        "Keeping trout, or fishing catch-and-release and fly-only areas, needs a Trout Conservation Stamp.",
    )),
    "SC": StateLicense(16, 16, "https://www.dnr.sc.gov/licenses/genlicense.html", (
        "South Carolina residents on military leave and privately owned freshwater ponds are exempt.",
    )),
    "SD": StateLicense(18, 18, "https://gfp.sd.gov/license-types/", (
        "Anglers 18 and older also need a Habitat Stamp. At 65 and older there's a reduced license, not an exemption.",
    )),
    "TN": StateLicense(13, 13, f"{_ER}/tennessee/fishing/license-exemptions", (
        "Farmland owners and tenants, and military on leave with orders, are exempt.",
        "Tennessee holds a Free Fishing Day each June. There's no statewide trout stamp, but some waters need their own permit.",
    )),
    "UT": StateLicense(12, 12, f"{_ER}/utah/fishing/licenses-and-permits", (
        "Under 12, a child may fish without one and keep a full daily limit. On Utah's Free Fishing Day each June, nobody needs a license.",
    )),
    "VT": StateLicense(15, 15, "https://vtfishandwildlife.com/licenses-and-lotteries/license-center/license-buying-faqs", (
        "Special licenses exist for blind or paraplegic people and for veterans with a disability of 60% or more.",
    )),
    "VA": StateLicense(16, 16, "https://dwr.virginia.gov/fishing/regulations/licenses/", (
        "Landowners on their own land, resident active-duty military on leave, guests in private ponds and legally blind people are exempt.",
        "Designated stocked trout waters need a trout license.",
    )),
    "WA": StateLicense(16, 16, "https://wdfw.wa.gov/licenses/fishing", (
        "Anglers 70 and older and disabled anglers get a reduced license, not an exemption. Salmon, steelhead and sturgeon need a catch record card.",
    )),
    "WV": StateLicense(15, 15, f"{_ER}/westvirginia/fishing/fishing-lincenses-and-fees", (
        "Licensed anglers fishing for trout also need a Trout Stamp.",
    )),
    "WI": StateLicense(16, 16, "https://dnr.wisconsin.gov/topic/Fishing/outreach/FishingLicenses", (
        "Anglers born before 1927 and resident military on leave are exempt. Trout may need an Inland Trout Stamp.",
    )),
    "WY": StateLicense(14, 14, f"{_ER}/wyoming/fishing/licenses-fees", (
        "Fishing preserves and waters under special or landowner fishing permits are the exceptions. Residents 14 to 17 can buy a cheap youth license.",
    )),
}


def license_age(code: str) -> int | None:
    """One age to state in a line, where residents and visitors share one."""
    entry = STATE_LICENSES.get(code)
    if entry is None or entry.resident_from != entry.nonresident_from:
        return None
    return entry.resident_from


def license_body(name: str, entry: StateLicense, agency: str) -> tuple[str, ...]:
    res, non = entry.resident_from, entry.nonresident_from
    if res is None:
        opening: tuple[str, ...] = ()
    elif res == non:
        opening = (f"In {name}, anglers {res} and older need a fishing license, residents and non-residents alike.",)
    else:
        opening = (f"In {name}, residents need a fishing license from {res}, and non-residents from {non}.",)
    return (*opening, *entry.notes, f"Rules and prices change: {agency}'s license page is the authority.")
