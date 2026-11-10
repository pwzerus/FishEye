"""Which state's rules apply (docs/adr/0027).

How to catch a fish is the same everywhere; what you may keep, what licence
you need and what the law asks of your boat is not. The guides and the
handbook are written once, for every state, except the passages that state
a rule. Those carry a region (a state code, `REGION_ALL` for the rest) and
are shown only where they apply.

This registry is what the rest of the app asks "who runs the rules here?".
Texas, Georgia and California have the most written up (licences, safety, a
first trip); 43 more states and DC have their bait rules (STATE_BAIT_RULES,
2026-11-01). The rest are listed so a person in one gets a straight
answer — "FishEye hasn't written this state's rules yet; they come from
<name>'s fish and wildlife agency" — instead of Texas's rules presented as
theirs.

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

from app.knowledge.species_guides import BAIT_RULES, SOURCES, TPWD_LIMITS_URL, Source
from app.knowledge.state_licenses import STATE_LICENSES, license_age

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

# Every other state's bait rules: from each agency's own regulations (or its
# eRegulations guide), read 2026-11-01, paraphrased as facts, each state's
# source in species_guides.SOURCES as "bait-<code>". Conditions kept; counts
# and sizes only where they are the rule. Not here: Alaska, Delaware, Hawaii,
# Montana and South Dakota, whose rules weren't in a page that could be read
# and checked (PDF only, or none found); they keep the "not written yet" answer.
STATE_BAIT_RULES: dict[str, tuple[str, ...]] = {
    "AL": (
        "Live baitfish (any fish or crayfish legal as bait) caught in Alabama's streams, rivers, public lakes or reservoirs may not be taken away from the water where they were caught, and live wild baitfish may not be brought in from outside Alabama.",
        'Bream (all species) may be used as bait if caught legally on hook and line and within the daily bream limit; no other game fish may be used as bait.',
        'Licensed anglers may take minnows, shad and certain suckers for bait with a cast net, small minnow basket or jug, dip net or a minnow seine up to 25 ft by 4 ft; no seines in un-impounded tributary streams and creeks; every game or other fish caught in them goes back at once.',
        'Fish, crayfish, snails and mussels, baitfish included, may not be released into public waters other than the one they came from (bait lost while fishing is fine).',
    ),
    "AR": (
        'Live baitfish, crayfish included, may be used only if caught in the same water, caught in a tributary flowing into it upstream (never moved upstream past a dam or barrier), or bought from a licensed dealer selling only certified farm-raised baitfish.',
        'On many AGFC lakes, common carp may not be used as bait (the lake-by-lake rules say which).',
    ),
    "AZ": (
        'Only the listed species may be used as live baitfish, and only in legal areas; dealers sell fathead minnows, golden shiners and goldfish. No live baitfish may be used or possessed on any waters in Coconino, Apache, Navajo, Pima and Cochise counties.',
        'Baitfish and crayfish caught on site must be used in that same water; live crayfish may not be carried away from the water where caught (except Yuma County and part of La Paz County).',
        'Except sunfish (genus Lepomis), the flesh of game fish may not be used as bait.',
        'Live baitfish may never be released into Arizona waters; bury unwanted baitfish on land away from the water.',
    ),
    "CO": (
        'East of the Continental Divide below 7,000 ft, live fish caught for bait may be used only in the water where they were caught. Collecting, using or possessing live fish as bait is prohibited east of the Divide above 7,000 ft and in all waters west of the Divide (except Navajo Reservoir), plus the Arkansas River above Parkdale and Watson Lake.',
        'Only minnows, bluegill, hybrid bluegill, carp, sunfish, gizzard shad, sculpin, white and longnose suckers, yellow perch and rainbow smelt may be taken and used as bait (alive or dead) for personal use; bag limits apply to sunfish, bluegill and yellow perch.',
        'Live bait from a commercial source must be carried with its receipt.',
        'Unused bait, crayfish included, must not go back into the water alive; west of the Divide crayfish must be killed right away or returned to the water they came from.',
    ),
    "CT": (
        'Any legally taken fish may be used as bait except largemouth bass, smallmouth bass, chain pickerel, northern pike, trout, salmon, carp and goldfish.',
        'Bait species (listed: shiners, fallfish, creek chub, dace, fathead and bluntnose minnows, white sucker, killifish, frogs except northern leopard frog, crayfish except rusty crayfish, some insect larvae...) may be taken for personal use with a licence: bait traps and umbrella nets anywhere, seines (up to 15 ft by 4 ft) in rivers and streams but not in most lakes and ponds; cast nets are banned inland.',
        'Where posted, taking, using or possessing fish as bait is prohibited on lakes and ponds.',
    ),
    "DC": (
        "The District has no bait restrictions of its own, but American shad, hickory shad, blueback herring and alewife may not be possessed (a coast-wide moratorium), so they can't be used as bait.",
        'Introducing any fish or other aquatic organism not native to DC waters is unlawful, so leftover bait from elsewhere must not go in the water.',
        'Cast nets and seines are banned; baitfish such as gizzard shad and shiners may be caught only with a dip net up to 24 in across. No nets at all, and no digging for bait, in Rock Creek Park.',
    ),
    "FL": (
        'Black bass and peacock bass, or any part of them, may not be used as bait; live goldfish and carp may not be used as bait.',
        'No live nonnative fish (except variable platys and fathead minnows) may be moved to or between waters for use as bait.',
        'Panfish (bluegill, redear and other bream, warmouth) and pickerel, whole or cut, may be used as bait by the angler who caught them, on rod and reel or pole and line only (not trotlines or bush hooks).',
        'Golden shiners, freshwater shrimp and other nongame fish under 8 in may be taken for bait with a cast net (mesh up to 1 in), minnow dip net, small seine or minnow trap; any game fish caught must be released at once.',
    ),
    "IA": (
        'Bait includes minnows (chubs, shiners, suckers, dace, stonerollers, bluntnose and fathead minnows...), green and orangespotted sunfish, gizzard shad (never live at any lake), frogs, crayfish and salamanders; game fish legally caught on hook and line may be used as bait.',
        'Dumping bait into Iowa lakes, rivers or streams is illegal: throw it in the trash, and swap bait-bucket water for tap or bottled water before leaving any water.',
        'Bait for personal use needs a sport fishing licence: tagged minnow traps up to 3 ft, dip net up to 4 ft, cast net up to 10 ft, seine up to 20 ft; Storm Lake crayfish stay in Storm Lake.',
    ),
    "ID": (
        'Live fish, leeches, frogs, salamanders, waterdogs and shrimp may not be used as bait anywhere in Idaho; live crayfish only if caught in the water being fished.',
        'Dead fish, fish parts, insects, worms and other natural baits are allowed; game fish may be used as bait if taken legally, and they count toward the bag and possession limits.',
        'Chumming is illegal, and no bait may be used on artificial-flies-and-lures-only waters.',
        'Minnows (nongame fish), yellow perch and crayfish may be trapped or seined only in waters open to fishing (seine up to 10 ft, 3/8 in mesh; tagged traps checked every 48 hours); other game fish caught go back alive, and netted fish must be killed except crayfish kept for bait on the same water.',
    ),
    "IL": (
        'Live bait fish you collect must be used on the water where you took them.',
        'Minnows (not bighead, black, grass or silver carp) and crayfish may be taken with licensed traps or minnow seines (up to 20 ft) for personal use only; mooneye, goldeye, skipjack herring and common carp may be cast-netted for live or dead bait on that same water; bighead, black, grass and silver carp only as dead bait there.',
        'Live injurious species may not be used as bait or possessed; endangered and threatened species may not be taken.',
    ),
    "IN": (
        'Any legally caught fish may be used as bait (game fish within their size and bag limits), but live carp and live gizzard shad may not; live shad are allowed only at Brookville, Cecil M. Harden, Monroe, Patoka, Freeman, Shafer and Hardy lakes and the Ohio River main stem (not embayments). Live goldfish are legal bait.',
        'Never dump a bait bucket or move live fish from one lake or river to another: releasing live fish is stocking and needs a DNR permit.',
        'Cast nets may take only bait fish and minnows (most waters; not within 200 yards below a dam), up to 20 ft across with mesh no larger than 3/4 in; endangered or threatened minnows may not be taken.',
    ),
    "KS": (
        'Legal bait: lures, prepared and vegetable baits, worms, crayfish, leeches, amphibians, mussels and baitfish (minnows, suckers, killifish and sunfish, but not black bass or crappie unless kept legally on hook and line within length and creel limits); prohibited, threatened or endangered species may not be used.',
        'Wild live baitfish, crayfish, leeches, amphibians and mussels may be used only within the drainage where caught, never above a dam or barrier upstream; bluegill and green sunfish from waters not designated for aquatic invasive species may be used anywhere in the state. Live bait from designated AIS waters (zebra mussels etc.) may not leave that water alive.',
        'Live baitfish may not be released into any water; dispose of them on land. Silver and bighead carp may not be kept alive.',
        'Bait may be taken with a seine (up to 15 ft by 4 ft, 1/4 in mesh; not on department-owned waters), a tagged fish trap, line, or a dip or cast net (mesh up to 1 in); limit 500 per person, at most 12 in long except gizzard shad and Asian carp.',
    ),
    "KY": (
        'Live bait fishes are rough fish (not Asian carp or federally listed species) and redear sunfish under 6 in; crayfish, salamanders, frogs (not bullfrogs), tadpoles, native lampreys, Asiatic clams and other aquatic invertebrates also count as live bait. Mussels (except Asiatic clams) may not be taken or used as bait.',
        'Live wild-caught shad, herring, mooneye and goldeye may be used only in the water they came from and not carried by road, even back to the same water.',
        'Personal bait gear: seines (10 ft by 4 ft; 30 ft by 6 ft on the Ohio and Mississippi rivers and Barkley and Kentucky lakes), minnow traps, dip nets, and cast nets up to 20 ft (not on lakes under 500 acres); possession limits such as 500 live bait fish and 500 crayfish.',
    ),
    "LA": (
        'Minnows, shad, crawfish and shrimp may be taken for bait with cast nets, minnow traps, small dip nets (frame up to 3 ft) and hand-worked bait seines up to 30 ft.',
        "Bream may be taken for personal bait in a trap up to 24 in long with a throat no larger than 1 by 3 in, marked with the angler's licence number; game fish may be taken for bait only by hook and line (or yo-yos and trigger devices).",
    ),
    "MA": (
        'For personal bait, live or dead, licensed anglers may take only banded killifish, fallfish, fathead minnow, golden shiner, mummichog, pumpkinseed, rainbow smelt, yellow perch and white sucker; smelt only on hook and line and only in the smelt season.',
        'Bait may be taken with one trap (openings up to 1 in), a circular net up to 6 ft across or a net up to 36 sq ft; gill nets are not allowed, and fish from inland waters may not be sold as bait.',
        'Frogs (not leopard frogs) up to 2.5 in may be used as bait, 10 a day.',
        'In the 8 catch-and-release areas only artificial lures may be used, and no bait may be carried.',
    ),
    "MD": (
        'In nontidal waters, seines (mesh up to 1/4 in, up to 6 ft by 4 ft) may be used only for minnows and bait fish, not within 50 ft of a dam or a river mouth; bait traps must be marked and checked daily.',
        'Bait fish may not be taken from Put-and-Take or Special Trout Management Areas, and minnows may not be used as bait in Deer and Swan creeks (Harford County).',
        'In the Monocacy and Upper Potomac basins, crayfish may be used as bait only with the head removed behind the eyes.',
        'No aquatic species may be released into Maryland waters except bait on a hook while fishing; no more than 1 quart of cut bait may be held while fishing.',
    ),
    "ME": (
        'Only the 16 species Maine law lists as baitfish (shiners, dace, fathead minnow, creek chub, fallfish, killifish, mummichog, suckers, American eel and a few others) and rainbow smelt may be used as bait in inland waters, live or dead.',
        'Not every water allows live or dead fish as bait: the general and special fishing laws list where they are banned, and live baitfish may not be kept in those waters.',
        'Bringing live fish or eggs into Maine, baitfish and smelt included, needs a permit; use locally caught legal baitfish.',
        'Baitfish may be taken for personal use with a licence; traps must be labelled and checked (every 7 days in the open-water months) and other fish released at once.',
    ),
    "MI": (
        'Baitfish may be used only in the waters where they were collected.',
        'Any legally taken fish and frogs may be used as bait except lampreys, live carp and goldfish.',
        'Crayfish not native to Michigan (red swamp crayfish among them) may not be used as bait alive or dead; rusty crayfish may be used only dead; no crayfish as bait on the Michigan-Wisconsin boundary waters.',
        'Throw unused bait (worms and their soil, crayfish, minnows) in the trash, never in the water.',
    ),
    "MN": (
        'Releasing bait into Minnesota waters, or onto land, is illegal: put unwanted bait in the trash.',
        'Live minnows and leeches may not be brought into Minnesota from another state.',
        'Water may not be carried away from a lake or river: to keep bait, drain the bait container on shore and refill it with bottled or dechlorinated tap water.',
    ),
    "MO": (
        'Live bait is crayfish, freshwater shrimp, some frogs and nongame fish; game fish or their parts may not be used as bait. Bighead and silver carp may be used only dead or cut.',
        "Live bait taken from Missouri's public waters may not be sold or taken to other states. Bait bought from a dealer must be on the Approved Aquatic Species List, with a dated receipt carried.",
        'Bait may be taken with a labelled trap (throat up to 1 1/2 in, checked every 24 hours), dip net, throw net, pole and line or a seine up to 20 ft by 4 ft; daily limit 150 crayfish, shrimp and nongame fish combined; bluegill, green sunfish and bullheads over 5 in (other nongame fish over 12 in) caught in nets or traps go back.',
    ),
    "MS": (
        'Game fish, nongame fish, goldfish and minnows may be used as bait if legally taken and within the daily creel limit; mussels may not be taken, held or used as bait.',
        'Residents may take shad and minnows for their own bait with dip or cast nets, boat-mounted scoops and wire baskets; minnow seines (up to 25 ft by 4 ft) and minnow traps may take minnows and nongame fish for bait.',
        'Releasing any aquatic species into public waters needs a permit from MDWFP.',
    ),
    "NC": (
        'Inland game fish may be used as bait if legally taken and within the size and creel limits of the water being fished.',
        'Nongame fish, crayfish and mollusks may be taken for bait or food with an inland licence, using a dip net up to 6 ft, a seine up to 12 ft (1/4 in mesh; any length on Lake Waccamaw), a cast net or small minnow traps; daily limit 200 combined, and they may not be sold.',
        'On the Roanoke River above the US 258 bridge, from April 1 to June 30 only a single barbless circle hook may be used with live or natural bait.',
    ),
    "ND": (
        'Legal live bait: leeches, and frogs, salamanders and crayfish native to North Dakota, plus only these live baitfish: fathead minnows, creek chubs and brook sticklebacks statewide; white suckers too on the Red and Bois de Sioux rivers, Lake Audubon, the Devils Lake complex and Stump Lake; white suckers and rainbow smelt on Lakes Sakakawea and Oahe and the Missouri and Yellowstone rivers. Some waters (listed) allow no live baitfish.',
        'No live aquatic organism may be brought into the state: fish, amphibians, aquatic insects and invertebrates.',
        'Game fish and their parts may not be used as bait, except yellow perch eyes and trout and salmon eggs; dead nongame fish or parts are legal; nightcrawlers and other land baits are always legal.',
    ),
    "NE": (
        'Baitfish, listed amphibians and crayfish may not be taken from public lakes, reservoirs or bayous (unless stated otherwise); digging and trapping are banned on state areas.',
        'In eastern Nebraska (the Missouri River below Gavins Point Dam and the rivers and streams east of the listed highways), live baitfish you seine may be used only in the water they came from.',
        'Red swamp, White River and rusty crayfish may not be used or held while fishing; personal limit 100 baitfish and amphibians; never dump baitfish or seining water into another water, and carry seined bait in domestic water.',
    ),
    "NH": (
        'Only listed species may be possessed and used as live bait: dace, common, emerald, golden and spottail shiners, creek chub and creek chubsucker, fallfish, killifish, lake chub, longnose sucker, rainbow smelt and silvery minnow (plus white suckers, which have their own trap rules).',
        'Daily limit 2 quarts of bait fish for personal use; up to 6 marked bait traps; drop nets only in waters without trout, and only small traps in trout waters.',
        'On designated trout ponds, live fish and their eggs may not be used as bait (salmon eggs are allowed).',
    ),
    "NJ": (
        'Only American eel, banded killifish, creek chub, fallfish, fathead minnow, gizzard shad, golden shiner, margined and tadpole madtoms and mummichog may be taken for bait: 35 a day combined, no more than 25 eels (eels at least 9 in).',
        'In trout-stocked waters, baitfish may be taken only by hook and line during the spring trout season.',
        'Herring may not be taken in fresh waters except some lakes in Morris, Passaic, Sussex and Warren counties and Spruce Run Reservoir (up to 6 in, 35, used there and released after the trip); elsewhere only bought herring (6 in or less) with a receipt dated within 7 days.',
    ),
    "NM": (
        'Using or possessing baitfish while fishing is illegal except in the approved drainages: fathead minnow, red shiner and shad in the Rio Grande, Pecos and Canadian drainages (golden shiner too at Elephant Butte and Caballo, white sucker in the Canadian), fathead minnow and red shiner in the San Juan, fathead minnow only in the Gila and San Francisco. Never in Special Trout Waters, Bitter Lake NWR or Bottomless Lakes State Park.',
        'Bluegill and other sunfish caught legally may be used as bait, live or dead, in the water where caught; common carp may be used dead (cut bait) statewide.',
        'Goldfish and bullfrogs (tadpoles included) may never be used as bait; commercially packaged dead fish are allowed wherever bait is.',
    ),
    "NV": (
        'In most of Nevada, fish may not be used as bait at all, alive or dead, except preserved salmon eggs and commercially prepared or preserved unprotected bait fish.',
        'The exception is Lake Mead, Lake Mohave and the Colorado River in Clark County: golden shiner, fathead minnow, threadfin shad and goldfish may be bought or caught there, and carp, gizzard shad and mosquitofish caught there may be used there, all only in those waters.',
        'Aquatic bait may be used only in the water it was taken from.',
    ),
    "NY": (
        'Only "green list" baitfish (golden, emerald, common and spottail shiners, fathead and bluntnose minnows, banded killifish, dace, white and northern hog suckers, creek chub, fallfish, madtoms, stonecat, logperch and a few others) may be bought and used in any water where fish are allowed as bait; a few others, such as alewife, only in the listed waters.',
        'Baitfish you catch yourself may be used only in the water where you caught them (a water includes its tributaries up to the first barrier) and may not be carried overland by car except in designated corridors.',
        'Some waters ban baitfish altogether (see the special regulations). Gear: seine or scap net up to 36 sq ft (sunrise to sunset, non-trout waters), marked minnow trap up to 20 in; cast nets only on the Hudson below the Troy Dam.',
    ),
    "OH": (
        'Forage fish, rough fish, and game fish with no possession or length limit on that water may be cut up for bait if the skin or head is left on so the species can be identified.',
        'No one but a licensed bait dealer may hold more than 100 crayfish, or 500 crayfish, minnows and other baitfish combined; clams and mussels may not be taken or used.',
        "No fish or aquatic invertebrate (crayfish, snails, insects) may be released into a water it didn't come from.",
        'Cast nets (up to 10 ft, mesh 1/4 to 1 in) may take only forage fish and minnows, not within 1,000 ft below a posted dam; minnow traps up to 24 by 12 in, tagged.',
    ),
    "OK": (
        'Bait for personal use may be seined, trapped, cast-netted or dip-netted year-round except at Lakes Taft, Lone Chimney, Overholser, Hefner and Draper, Close to Home waters, the Wichita Mountains refuge and Department fishing areas; cast nets are banned on the Scenic Rivers (except one stretch of the Illinois River).',
        'Game fish and nongame fish not commonly used as bait must be released at once. Limits: 25 nongame bait fish from rivers and streams (200 shad); no more than 200 nongame bait fish, shad included, carried by land.',
        "Shad from Oklahoma waters may not be sold or taken out of state to sell; unattended containers holding live bait must carry the angler's customer ID and be checked every 24 hours.",
    ),
    "OR": (
        'Dead fish, preserved fish, fish and shellfish parts and fish eggs may be used as bait.',
        'Live fish may not be used as bait in fresh water (live nongame fish only in the ocean, bays and tidewaters where they were caught); goldfish, lamprey, live crayfish, live leeches and ornamental fish may not be used, and goldfish and live leeches may not even be carried while angling.',
        'Bringing live fish or eggs into Oregon, moving them overland or from one water to another, or holding live fish in Oregon waters needs an ODFW permit.',
    ),
    "PA": (
        'Baitfish are minnows, suckers, chubs, fallfish, lampreys, gizzard shad up to 8 in, darters, killifish and stonecats (not threatened or endangered ones); legally taken game fish may also be used as bait. Goldfish, comets, koi and common carp may not be used or held as bait while fishing.',
        "Live baitfish may not be released into any water except on a hook, and a baitfish may not be moved into another drainage where that species doesn't already live.",
        'Limit 50 baitfish and fishbait (crayfish, aquatic insect larvae) a day; bought bait is covered by its receipt for 15 days. Stocked trout waters are closed to taking bait from February 17 to opening day, and most special trout waters always.',
    ),
    "RI": (
        'Goldfish may not be used as bait in fresh or estuarine waters, and nonnative bait fish, including goldfish, green sunfish and fathead minnows, may not be imported, sold or held for bait.',
        'Releasing any live fish or invertebrate bait into fresh water is prohibited.',
        'Nets and seines may not take fish in fresh water except to land a hooked fish or to catch baitfish; cast nets are banned. Holding more than 100 live freshwater minnows, or selling them, needs a DEM licence. Corn and chumming are banned on designated trout waters.',
    ),
    "SC": (
        'No game fish may be used as bait except bream (not redbreast sunfish); trout only on Lakes Hartwell, Russell, Thurmond, Tugaloo, Yonah, Stevens Creek Reservoir and the Savannah River. Game fish used as bait count toward the daily creel limit.',
        'Nonnative fish not already established in the water being fished may not be used as bait, except fathead minnows, golden shiners and goldfish (including black salties).',
        "Releasing any aquatic species, bait included, into South Carolina waters needs a permit (bait lost while fishing excepted); don't dump the bait bucket.",
    ),
    "TN": (
        'Live fish, crayfish and salamanders may never be released into Tennessee waters other than the ones they came from.',
        'Licensed anglers may take game fish (trout and sunfish included) for bait by sport-fishing methods, within the creel, length and season rules of both the water they came from and the water they are used in; trout from the South Fork Holston, Watauga, Doe and North rivers may be used only where they were caught.',
        'Class A bait fish (skipjack herring, gizzard and threadfin shad, fathead minnow, golden shiner, goldfish and others on the list) may be caught, bought and moved as bait; skipjack herring are limited to 100 a day.',
    ),
    "UT": (
        'Using or holding live baitfish while fishing is unlawful (except where the Fishing Guidebook allows it); tiger salamanders may not be used, live or dead.',
        'Commercially prepared, chemically treated baitfish and the eggs of legally caught fish may be used wherever bait is allowed; live crayfish only on the water where they were caught.',
        'No bait at all on artificial-fly-and-lure-only waters; baitfish, live or dead, may not be carried from a water declared infested with an invasive species to any other water.',
    ),
    "VA": (
        'Any legally kept game fish may be used as bait whole, within creel and length limits; only bluegill, sunfish and bream may be cut up. Game fish may not be used as bait on trotlines, juglines or limblines.',
        'Personal bait limit: 50 minnows, chubs, madtoms, crayfish and hellgrammites combined (no more than 20 crayfish); salamanders may not be held. Crayfish may be used only in the water where caught, and not collected in the Big Sandy drainage.',
        'Fathead minnows, golden shiners and goldfish are unlimited; gizzard and threadfin shad only in certain waters; only hatchery-raised trout, with a bill of sale, may be used as bait; bought bait needs a receipt listing number and species.',
    ),
    "VT": (
        'Vermont is split into an Eastern and a Western baitfish zone: baitfish bought or caught may be used in several waters, but only within the same zone. Keep the purchase receipt; harvesting your own needs a Wild Baitfish Endorsement.',
        'Restricted waters (those with invasive species, such as Lake Champlain and the Connecticut River with their listed tributaries): baitfish used or caught there may not be taken to or used in any other water.',
    ),
    "WA": (
        'In fresh water, live aquatic animals may not be used or possessed as bait, except: live animals other than fish collected from the water being fished, live sand shrimp, and live forage fish in the Columbia River below the Rocky Point to Tongue Point line.',
        'Bait (any substance that attracts fish) is banned where the special rules say so; when fishing for trout with bait, every legal-size trout caught counts toward the daily limit, kept or released.',
    ),
    "WI": (
        'Minnows bought from a Wisconsin bait dealer may be taken home and used again on the same water, or anywhere if no lake or river water was added to the container (up to 2 gallons of water to keep them alive, no other fish in it).',
        'Minnows you catch yourself may be used only on the water where you caught them and may not leave it alive; minnow harvest is closed on VHS waters (the Winnebago system, the Great Lakes, the Mississippi and the Wisconsin River below Prairie du Sac Dam).',
        'Drain all water from the boat, livewells and bait containers when leaving; throw unwanted minnows in the trash, or take them home dead and preserve them for later.',
    ),
    "WV": (
        'Darters may never be possessed: check the bait bucket and put any back or destroy them.',
        'In the East and West Forks of the Greenbrier, the upper Gauley and its rivers, Camp Creek, Manns Creek and the other listed waters (and their tributaries), no fish at all, not even dead packaged minnows, may be used as bait, and no nongame fish may be kept.',
        "No fish may be released anywhere but where it was caught: don't release unused baitfish. Licensed anglers may hold up to 50 crayfish for bait; live minnows are banned on catch-and-release waters.",
    ),
    "WY": (
        "Live baitfish may be used only in select waters east of the Continental Divide: if a water isn't named in the fishing regulations' live baitfish sections, live baitfish are not allowed there.",
        "Wyoming's five drainage areas each have their own rules for where live baitfish may be used, which kinds, and where they may come from; rules can differ along the same river (such as the North Platte).",
    ),
}
# Where the rules forbid what the guides recommend (live minnows) in most
# waters, every bait question there shows them, as California's do.
_LIVE_FISH_LIMITED = {"AZ", "CO", "ID", "NM", "NV", "OR", "UT", "WA", "WY"}

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


# Where one page doesn't hold all of a state's bait rules (checked 2026-11-06).
_MORE_BAIT_SOURCES: dict[str, tuple[str, ...]] = {"NC": ("bait-nc-nongame",)}


def _uncovered(code: str, name: str) -> Jurisdiction:
    agency, short, limits_url, license_url = _AGENCIES.get(code, (None, None, None, None))
    bait = STATE_BAIT_RULES.get(code, ())
    return Jurisdiction(
        code=code, name=name, agency=agency, agency_short=short, limits_url=limits_url, license_url=license_url,
        bait_rules=bait,
        bait_rules_source_ids=(f"bait-{code.lower()}", *_MORE_BAIT_SOURCES.get(code, ())) if bait else (),
        bait_rules_on_every_bait_question=code in _LIVE_FISH_LIMITED,
        license_from_age=license_age(code),
        license_topic=f"rule-license-{code.lower()}" if code in STATE_LICENSES else None,
    )


JURISDICTIONS: dict[str, Jurisdiction] = {
    code: _COVERED.get(code) or _uncovered(code, name)
    for code, name in sorted(STATE_NAMES.items(), key=lambda kv: kv[1])
}


# Who needs a license, per state: its page, named after the agency.
SOURCES.update(
    {
        f"license-{code.lower()}": Source(
            f"license-{code.lower()}", f"{JURISDICTIONS[code].agency_label}: fishing license rules", entry.url, "agency"
        )
        for code, entry in STATE_LICENSES.items()
    }
)

# How many fish may be kept, and how big, per state: the agency's limits page
# (added 2026-11-08). The numbers aren't copied: they change every year. The
# three states with written rules keep their agencies' prefixes, as their
# other pages do.
_LIMITS_SOURCE_IDS = {"TX": "tpwd-limits", "GA": "garegs-limits", "CA": "cdfw-limits"}


def limits_source_id(code: str) -> str:
    return _LIMITS_SOURCE_IDS.get(code, f"limits-{code.lower()}")


SOURCES.update(
    {
        limits_source_id(code): Source(
            limits_source_id(code), f"{j.agency_label}: size and bag limits", j.limits_url, "agency"
        )
        for code, j in JURISDICTIONS.items()
        if j.limits_url
    }
)


def normalize(code: str | None) -> str | None:
    """"tx" -> "TX"; anything that isn't a state code -> None."""
    code = (code or "").strip().upper()
    return code if code in JURISDICTIONS else None


def get(code: str | None) -> Jurisdiction | None:
    key = normalize(code)
    return JURISDICTIONS[key] if key else None


# With no state given, these states' rules may still show: each names its
# state in its own text ("In Texas ..."), so it can't be mistaken for a
# general rule, and a person who hasn't said where they are still gets an
# answer. Not the forty-odd states with bait rules only: with all of them
# in play, any question about bait drew some state's rules (2026-11-01).
_SHOWN_WITHOUT_A_STATE = frozenset(_COVERED)


def rules_written_in_full(state: str | None) -> bool:
    """Licences, safety and a first trip, not only the bait rules."""
    return state in _COVERED


def applies(region: str, state: str | None) -> bool:
    """May a passage with this region be shown to someone in `state`?"""
    if region == REGION_ALL or region == state:
        return True
    return state is None and region in _SHOWN_WITHOUT_A_STATE


def covered() -> list[Jurisdiction]:
    return [c for c in JURISDICTIONS.values() if c.covered]


def covered_names() -> str:
    """"Georgia and Texas" — for sentences; past a handful, how many:
    "45 states and Washington, D.C."."""
    names = [c.name for c in covered()]
    if len(names) > 5:
        n, dc = covered_count()
        return f"{n} states" + (" and Washington, D.C." if dc else "")
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def covered_count() -> tuple[int, bool]:
    """How many states have rules written, and whether DC does."""
    codes = {c.code for c in covered()}
    return len(codes - {"DC"}), "DC" in codes


def license_count() -> tuple[int, bool]:
    """How many states have their license rule written, and whether DC does."""
    codes = {j.code for j in JURISDICTIONS.values() if j.license_topic}
    return len(codes - {"DC"}), "DC" in codes


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
    n, dc = covered_count()
    covered_zh = (
        f"{n}个州" + ("和华盛顿特区" if dc else "")
        if len(covered()) > 5
        else "、".join(ZH_STATE_NAMES.get(c.code, c.name) for c in covered())
    )
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
