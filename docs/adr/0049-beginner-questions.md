# 0049. What beginners ask: new handbook cards, a limits card per state

Date: 2026-11-08. Status: accepted (local, not deployed).

## Context

The product owner asked whether the questions beginners post on Reddit and
fishing forums could be answered by Ask, and stored in the guides. Their
photos and words can't be used: the posters own them, and Reddit's terms
(which neither of Claude's tools could open) don't license them to others.
The data-sourcing skill now has a QUESTIONS ONLY class for forums
(docs/data-sources.md, "Beginner questions from forums"): a question may be
stored only as a paraphrase in our own words, never a post's text, answers,
photos, names or links, and a forum answer is never a source. Of the
forums checked, BD Outdoors and Anglerboard allow it; Reddit, Xiaohongshu,
Zhihu, Baidu Tieba and most US forums don't, by robots.txt, terms or a bot
check.

## Decision

**A question set, put to Ask before writing anything.** 159 beginner
questions written for FishEye (gear, rigging, bait, where and when, bites
and landing, things going wrong, keeping and cooking, rules, safety and
manners, single fish; 15 in Chinese, 10 in Spanish) and 18 paraphrased from
BD Outdoors and Anglerboard threads, run through `search_guides` (no model,
no cost) and judged by reading what came back.

**What they found, and what was written** (`knowledge/angling_handbook.py`,
from state agency pages as facts in our own words, and National Weather
Service and USFWS pages, which are public domain):
- Bites and hooksets, and playing and landing a fish (`technique-bite`,
  `technique-landing`); a swallowed hook (`care-deep-hook`).
- A new category, "When it isn't working": no bites, bait taken but nothing
  hooked, snags, line twist (`trouble-*`).
- Manners on the bank (`rule-manners`), taking kids fishing (`method-kids`),
  lightning, heat and falling into cold water (`safe-lightning`,
  `safe-heat`, `safe-cold-water`).
- Rod length added to `tackle-rods`.
- **"How many can I keep, how big?"** was answered with whatever fish
  passage shared a word. Every state now has a card (`rule-limits-xx`)
  saying the limits differ by fish and by water and pointing to the
  agency's limits page; the numbers aren't copied, because they change.
  A limits question in a known state, or a "two rods" question where the
  license card covers it (California's Second Rod validation), puts that
  state's card first (`ask._with_required_rule`); the state's own card on
  the subject, if it ranked first (Georgia's "keeping fish within the
  limit"), stays above it.
- The topic gate turned away "do I need a swivel", "my knot keeps coming
  undone", "do I need a landing net", "what happens if I fall into cold
  water" and "how many bass can I keep"; the words and phrases are added.
  The Chinese and Spanish glossaries gained the words that found nothing
  (卸力, 挂底, 打雷, 没口; pican, peces, atoró, trueno).

**Kept as an eval set.** 69 of the questions, with the passages that answer
them, are `eval/rag_cases.BEGINNER_CASES`, reported by `rag_runner`; the
state rules are tests (`tests/test_beginner_questions.py`).

## Results

Measured before and after on the same code otherwise (a copy of the app
without these changes), state-less as the eval runs:

| | Before | After |
|---|---|---|
| Beginner questions, hybrid (as served) | 42/69 | 68/69 |
| Beginner questions, keyword only (tests, CI) | — | 54/69 |
| Original set, hybrid | 99.0% | 99.0% |
| Every other set (Chinese, paraphrase, rephrased, untuned, new topics, off-topic, not covered), both modes | — | unchanged or better |

Adding 62 passages moved some old answers down by one place (BM25's average
length and IDF change with the corpus; the semantic side contributes its
top 5). Each was found by comparing with the copy and fixed in the wording
of the card involved, not by relabelling, except two cases where a new card
is itself an answer (`kid-pole`, `para-kid-reel`: Taking kids fishing names
the spincast reel and why it tangles less).

## Consequences

- Still not covered, for want of a page that could be read as HTML: caring
  for a rod and reel, when to change line, a hook in your own skin,
  muddy-tasting fish. Take Me Fishing answered 403 to the browser this time.
- Keyword-only search (RAG_SEMANTIC=off: the tests and `.claude/launch.json`)
  answers the beginner questions much worse than the served hybrid
  (78% against 99%): "I've been fishing for hours and haven't had a single
  bite" finds a perch setup. A local check of Ask should run with the
  semantic model on.
- Spanish questions aren't in the eval set: the retriever doesn't translate,
  `search_guides` does. They were checked through `search_guides`.
- Each new card needs the four title translations in
  `frontend/src/i18n/names.ts`; the limits cards use a template, like the
  license cards.
- `cadbw-safety` (dbw.parks.ca.gov) is cited by the California life jacket
  card although docs/data-sources.md lists that site as FORBIDDEN; found in
  passing, not changed here.

## Addendum, later on 2026-11-08: a second pass over the forums

The same two forums were read again, 21 more pages of thread titles (BD
Outdoors 13, Anglerboard 8, including Anglerboard's board for new anglers'
questions), under the same rule: a question is kept only as a paraphrase.
70 questions were put to Ask's search (no model, no cost).

What they found, and what was done:
- "How can I tell if a fish has gone bad" was answered with fish
  identification. New card `care-fresh-or-spoiled`, from the FDA's seafood
  safety page (public domain) and New York's beginners' guide: smell, eyes,
  gills, firm flesh, edges of a fillet, two days in the refrigerator.
- Nothing said what to wear. New card `safe-clothing`, from the Minnesota,
  New York and Texas booklets (docs/adr/0050): layers and a windproof shell,
  no jeans in the cold, sturdy shoes, a brimmed hat and polarized glasses,
  rain gear, sunscreen, and washing sunscreen off your palms before
  handling bait.
- The gate turned away "I haven't caught anything all year", "are tungsten
  weights worth it" and "how long does braided line last": "caught/catch/
  catching anything", "braided line" and "tungsten" now admit them. The
  line card says that braid wears out too.
- Still unanswered, for want of a source: fish that follow a lure but don't
  bite, putting line on a baitcaster, attaching a reel to a rod, finding the
  depth under a bobber, smoking fish, pond management, swapping treble hooks
  for singles, and "what fish did I catch" (the photo check answers that,
  but Ask doesn't point to it).

14 of the questions are in `BEGINNER_CASES`. Served search: 81/83 (the 69
earlier cases unchanged, all 14 new ones found). Keyword-only: 66/83, every
earlier case unchanged, 13 of the 14 new ones found.
