# ADR 0028: Georgia, the second state

## Status
Accepted. The first use of ADR 0027's "a state is data" claim, and the
change that claim needed once there were two states.

## Context

ADR 0027 split the content into knowledge for every state and rules tagged
with one state, with Texas the only state written. Adding Georgia tests
whether a new state really is a data change.

## Decision

**Sources: Georgia's own pages only, all opened.** The DNR Wildlife
Resources Division's site (licences, required boating equipment, Clean
Drain Dry, angler resources, state-park fishing) and the online edition of
its 2026 regulations guide (licence requirements, general freshwater
regulations, fishing methods, boating, agreements with bordering states).
WRD's own copy of the guide is a flip-book that can't be cited by page; the
online edition carries the DNR Commissioner's message and is the one cited.
Ten sources, `gawrd-*` and `garegs-*`.

**What was written.** Same rules as Texas: paraphrased closely, conditions
kept, no creel or length numbers (they change and vary by lake; the page
links the agency's limits instead).

- `Jurisdiction("GA")`: Georgia WRD, its limits and licence pages, and its
  bait rules (game fish as bait, cast nets for shad and herring and where
  they are banned, minnow seines and traps, never moving bait, no live
  blueback herring on the lakes shared with Alabama).
- Handbook topics tagged `GA`: the licence (16 and older; private ponds and
  own land; trout licence and the free saltwater SIP permit; licences valid
  on waters shared with Alabama and South Carolina), the life-jacket law,
  Clean Drain Dry as WRD asks it (hot water, five days' drying; WRD presents
  it as practice, not law, so the card doesn't call it law), keeping fish
  within the limit, and a first trip (where to fish, forecasts, Fish-n-Learn,
  borrowing tackle at state parks).
- Bait rules moved from a single shared passage onto each `Jurisdiction`:
  one passage per state (`bait_rules` for Texas, kept for existing links;
  `bait_rules-ga`), and one card per state on the guide page.
- The old "Life jackets" card mixed Texas law with advice for everyone. It
  is now a general card (fit, why to wear one) plus one law card per state,
  so someone in Colorado still gets the advice. Texas's rule cards gained
  "(Texas)" in their titles so two states' cards read apart.

**One code change the data needed: a search index per state**
(`services/rag/regional.py`). ADR 0027 filtered other states' passages out
after searching, and noted the risk. With two states it failed at once: a
question naming a fish keeps only one or two slots for shared passages,
Texas's bait rules took them, and a Georgia angler asking "is it legal to
use a small bass as live bait" got nothing. Each state now searches its own
view — general content plus its own rules — built once and cached; all
uncovered states share one view. The hybrid view reuses the passage vectors.
The full index is still searched once, only to tell a rules question
("the best match is some state's rule") from a general one.

A covered state asked about a rule it has no card for (Georgia has no
filleting rule card; Texas does) gets "FishEye has written some of
Georgia's rules, but not this one", not Texas's.

**Found on the way:** "license" (how people type it) didn't match "licence"
(how the guides spell it) in keyword search, so "does my 10 year old need a
fishing license" missed the licence card for Texas too. Fixed with a
synonym; the keyword new-topics score went from 85% to 88%.

## Results

- Backend 593 tests, frontend 209. New: Georgia's rule passages are tagged
  and cite only Georgia sources; seven Georgia questions (English and
  Chinese) find Georgia's card and no Texas card; Texas never sees
  Georgia's; how-to answers are identical in Texas, Georgia and Colorado;
  the per-state views.
- Retrieval eval (no state chosen): unchanged for hybrid; keyword MRR 0.85
  to 0.86. With no state chosen both states' rule cards are right answers,
  and the eval's rule cases now accept either.
- In the browser: Georgia shows 65 handbook cards (5 Georgia rule cards, no
  Texas ones), Georgia's bait rules and Georgia WRD's limits link; Texas the
  mirror image; no state shows both, labelled.

## Known gaps

- Saltwater: Georgia's SIP permit is mentioned, but FishEye has no saltwater
  content for any state.
- Range and example text in the species guides is still Texas's (ADR 0027).
- Keyword-only search still misses some phrasings ("where can I borrow a
  fishing rod" doesn't reach the first-trip card); the semantic model helps
  there, as for every topic.
- Adding a state took one source module edit, one registry entry, six
  handbook topics and their tests. The per-state index is built lazily;
  with many states the first question from each costs one index build
  (milliseconds for keyword, no re-encoding for hybrid).
