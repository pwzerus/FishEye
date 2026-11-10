# 46. Learning to fish first; more lake fish in the photo check and in Ask

Date: 2026-11-06

## Context

The product owner set the site's purpose plainly: FishEye teaches people to
fish (where to go, what to use and why it works, the rules) and photo ID is
a side tool, not the selling point. Testing it with photos found online, a
steelhead came out as "Not sure… Rainbow Trout 70%": right species, but it
read as a mistake, under a list of more than 40 state agencies. Steelhead,
salmon, lake trout and sturgeon, common in the Great Lakes, had no class in
the photo check and no answer in Ask ("salmon" was on Ask's no-guide list).

## Decision

**Learning first in what people see.** The home page, the site description
and the link previews talk about learning (where to go, what to use and why
it works, the rules); "photo ID" is gone from the previews. The home page's
cards start with learning a fish, then the rules.

**A rules page per state** (`app/rules`, `app/rules/[state]`, in the
sitemap): who needs a license, the agency's limits page (FishEye never
states a limit), what may go on the hook, and that state's own handbook
topics. The address is the state's name (`/rules/new-york`), what people
search for. With no state chosen, the limits line asks for the state instead
of listing every agency.

**The photo answer names the fish.** Above 50% the likeliest fish is named as
the best guess with the others under it, rather than a bare "not sure". A
fish with two names (a steelhead is a rainbow trout, `SAME_FISH`) is named
by the one the photo shows, says what it is, and links the guide it shares;
the two names' shares count together towards "sure". Steelhead also backs a
claim of rainbow trout on a catch.

**More classes** (`services/fish_id_classes.py`): the six fish that got
guides since the last build become guide classes, golden trout, kokanee and
brown bullhead get classes of their own, and 22 lake fish join as fish with
no guide: steelhead, Chinook, coho, pink and Atlantic salmon, bull trout,
arctic grayling, lake whitefish, cisco, three sturgeons, paddlefish, burbot,
rainbow smelt, alewife, round goby, northern snakehead, butterfly peacock
bass, shorthead redhorse, shortnose gar. The image encoder is unchanged, so
only the text vectors were rebuilt (`build_fish_id_model --text-only`) and
the head refitted. Steelhead has no species of its own, so its photos come
from Wikimedia Commons files their uploader calls steelhead (public domain,
CC0 or CC BY only; `cli/fish_id_commons.py`), split by photographer between
training and test.

**A second test set** from Commons (`fishid_cache/commons/`, up to 15 photos
per fish class from its species category): pictures like the ones people
find online, not only iNaturalist's. Measuring only.

**Ask knows the cold-water fish.** Twelve handbook topics, written from
NOAA, Minnesota DNR, New York DEC and Iowa DNR pages (and a 1904 Bureau of
Fisheries paper on the lateral line): steelhead or rainbow, telling the
salmon apart, whitefish and cisco, when the runs are, fishing a river for
steelhead, Great Lakes trolling, lake trout, sturgeon, ice fishing for perch,
drifting bait for stream trout, the summer thermocline, and why bait works.
Fish the handbook covers but no guide does (`TOPIC_FISH`) are answered from
those topics first, are masked so "lake trout" isn't read as the trout
guides, and aren't refused; a kitchen question ("how do I cook salmon")
still is. Their names are in the four other languages' glossaries.

## Consequences

- Measured (reports/fish-id-2026-11-06.md), right top answer, old head → new:
  on iNaturalist test photos 67.6% → 78.0% overall and 83.3% → 82.6% on the
  original 18 guide fish; on the Commons test half 44.6% → 65.0% and 75.2% →
  77.0%. A claim of another kind of fish is accepted 0.0% (14 of 30,383).
- Steelhead can't be told from rainbow trout by photo (0 of 18 named as
  such; 5 as rainbow trout): the answer leads with the species and explains.
- Some new fish have few openly licensed photos (iNaturalist's default
  licence is CC BY-NC), so their training is thin and their answers less sure.
- `LimitsNote` no longer takes `texasUrl`; callers still pass it, harmlessly.
