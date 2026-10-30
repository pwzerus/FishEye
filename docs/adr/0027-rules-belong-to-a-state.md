# ADR 0027: Fishing rules belong to a state, not to the app

## Status
Accepted. Extends ADRs 0011 (species guides), 0024 (the handbook) and 0026
(honest empty answers). The map was already national (the "All states" mode);
this brings the guides and Ask in line with it.

## Context

The guides were written while FishEye was a Texas app, and it showed in four
places:

1. **Rule passages stated as if they were everyone's.** The bait rules, the
   licence, the life-jacket rule, clean-drain-dry, "when you may fillet a
   fish" and "your first trip" are Texas law and Texas agencies, indexed as
   ordinary passages. Someone in Colorado asking "do I need a fishing
   licence" was told, confidently, what Texas requires. That is worse than
   not answering.
2. **One agency, hard-coded.** Every fish page linked TPWD's limits page
   (`TPWD_LIMITS_URL` in the species API), the home page footer named TPWD,
   and the pages said "Texas freshwater fish".
3. **No notion of where the person is.** The map knows which state was
   entered; Ask, the handbook and the guides had no way to ask.
4. **The fish are not Texas's.** What a largemouth eats, how to tie a
   palomar knot and how to clean a crappie are the same in every state. Only
   the rules, and some of the examples ("found all over Texas"), are local.

Left as it was, FishEye would be useless outside Texas, and worse, wrong in
a way that looks right.

## Decision

**Two layers.** Knowledge that applies everywhere is written once. Anything
that states a rule is tagged with a state and shown only where it applies.

- `knowledge/jurisdictions.py`: a registry of the 50 states and DC. Each has
  a name; the covered ones also have the agency and its limits and licence
  pages. Texas is the only covered state. For the others there is no agency
  and no link, on purpose: a link FishEye hasn't reviewed would be a guess
  presented as a source. Adding a state is a new `Jurisdiction` plus its
  tagged passages, and nothing else in the code names a state.
- `Passage.region` and `HandbookTopic.region`: a state code, or `"all"`.
  Tagged `TX`: the bait rules, and the handbook topics `care-filleting-rule`,
  `start-first-trip`, `safe-lifejacket`, `rule-license` and
  `rule-clean-drain-dry`. Topics that mixed a general fact with a Texas
  example (eating safely, measuring a fish) were reworded: the general rule
  first, Texas's agency as the example.
- Ask takes an optional `state`. Passages of other states are removed from
  the answer. **If the best match is another state's rule, nothing is shown:**
  what ranks below it is filler, and filler under a rules question reads as
  an answer (found by the first version of the tests, which returned
  rainbow-trout passages for "do I need a licence" in Colorado). The reply
  is a fourth kind of empty answer, `other_state`: it names the state,
  says what FishEye has written so far, and points to that state's agency.
- With **no state chosen, nothing is hidden**. The rule passages say "In
  Texas ..." in their own words and carry a "TX rules" badge, so they can't
  be mistaken for a general rule, and a visitor who hasn't said where they
  are still gets an answer.
- The frontend remembers the choice (`localStorage`, shared by every page via
  `lib/jurisdiction.ts`). It is set by entering a state on the map or by a
  "Fishing in" picker on Ask and the fish guide, which lists the states with
  rules written first. Regional handbook cards, the bait-rules card and the
  limits note go through `RegionGate`: shown to that state and to people who
  haven't chosen, replaced by "Bait rules differ by state" for anyone else.
- `GET /api/jurisdictions` serves the registry so the frontend never names an
  agency itself.
- All "Texas"/"TPWD" copy that spoke for the whole app was reworded: the home
  page, the fish guide, Ask's coverage line.

## Results

- Backend 577 tests (21 new in `test_jurisdictions.py`), frontend 204 (14
  new). The retrieval eval is unchanged: the same 98 / 28 / 34 / 33 sets give
  the same numbers, since the filter only acts when a state is given.
- The tests that matter most: a rules question from another state returns no
  Texas passage; the same question in Texas or with no state returns the
  licence; how-to questions return the same passages in every state; and no
  untagged shared passage states a Texas rule.

## Known gaps

- Only Texas has rules. Every other state gets an honest "not written yet"
  and a pointer, not an answer. Writing a state means reading its agency's
  pages (ADR 0011's rule: nothing from a source that wasn't opened).
- **Ranges and examples are still Texas's.** Species guides say "native to
  East Texas" or "found all over Texas", and the seasonal notes ("winter is
  prime for blue catfish in Texas") are Texas facts. They are true and are
  not stated as rules, so they are not tagged, but a reader in another state
  sees Texas examples. The Ask coverage line and the fish page say so. The
  fix is regional notes per state, not rewriting the guides.
- The 18 species were chosen for Texas. Guadalupe bass is a Texas native
  with a small range elsewhere; a state's guide set will differ.
- The state is remembered per browser, and is only set by the map's state
  click or the picker, not by search or "use my location".
- The retriever itself is not region-aware: the filter runs after retrieval
  with four spare hits. Cheap and enough while regional passages are few;
  with many states' rules in the index, region should become a retrieval
  filter so each state's rules compete only with each other.

## Update, 2026-10-29: a state named in the question

The product review of 2026-10-28 asked "do I need a fishing license in
Minnesota" with no state picked and got Texas's, Georgia's and
California's licence rules: the question named a state, but only the
picker set one. Now `jurisdictions.state_in_question` reads a state named
in the question, in English or Chinese ("Minnesota", "明尼苏达", "得州"), and
it wins over the picked state (`rag/ask.answer_state`): someone asking about
Minnesota wants Minnesota's rules wherever they are. Rigs and fish named
after a state (Texas rig, Kentucky bass) and Kansas City don't count, and a
question naming two states names none. A question in Chinese gets the
passages' intro and the other-state answer in Chinese.
