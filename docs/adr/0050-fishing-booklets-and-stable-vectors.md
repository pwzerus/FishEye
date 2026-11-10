# 0050. Learning from state fishing booklets; passage vectors that hold still

Date: 2026-11-08. Status: accepted (local, not deployed).

## Context

ADR 0049 left four beginner topics unwritten because the only agency pages
on them were PDFs: caring for a rod and reel, when to change line, a hook in
your own skin, and muddy-tasting fish. The product owner asked for free
fishing books in PDF to be found, downloaded into `docs/learn-material/` and
learned from, for beginners and experienced anglers, on rods, sinkers and
every other part of the tackle.

Free and legal are not the same thing. The commercial books (the "For
Dummies" kind) are not free, and a free PDF of one is a pirated copy. What
is both free and lawful to learn from is what state fish and wildlife
agencies publish for their angler-education programs: booklets, lesson
plans and tip sheets, written for beginners and the people who teach them.

## Decision

**Official booklets only, as facts + link.** 26 PDFs from Texas Parks and
Wildlife, New York DEC, Minnesota DNR (the MinnAqua leader's guide),
Oklahoma DWC and Wisconsin DNR, plus Kentucky's "Basic Fishing", which the
product owner had saved (docs/data-sources.md, "Fishing-education
booklets"). They are copyrighted or carry no licence, so they are
RESTRICTED: the handbook takes facts from them in its own words and cites
them, never their sentences, tables or drawings. The files stay in
`docs/learn-material/`, git-ignored. Kentucky's booklet says it is "intended
to be used by not-for-profit organizations", so it is not cited, and
nothing rests on it alone.

**What was written** (`knowledge/angling_handbook.py`):
- Looking after your rod, reel and tackle (`tackle-care`): cleaning and
  oiling, no hose, storing with the drag backed off, rinsing after
  saltwater, a damp tackle box, soft plastics that melt together.
- Changing your fishing line (`tackle-new-line`): every year, sooner when
  it snaps in a knot or curls, pre-filled reels, line weights, putting line
  on a spincast reel, not overfilling.
- Spincast reel won't cast or won't reel in (`trouble-spincast`).
- A fish hook in your skin (`safe-hook-injury`): back it out only if the
  barb isn't in; a buried barb or a hook near the eye goes to a clinic,
  covered with a paper cup; tetanus; how not to get hooked.
- Black spots in a fillet (`care-black-spots`): a parasite, killed by
  cooking.
- Lead sinkers and wildlife (`tackle-lead`), trimming a fillet's dark strip
  and fat (`clean-trim-fillet`), and catching stocked rainbow trout
  (`method-stocked-trout`).
- A sentence each in Snags (look away as you pull), Line twist, Keeping
  your catch (a stringer through the lip, not the gills), Rod power (the
  label above the handle), Setting the drag (line that breaks on a run),
  Is it a bite (the bobber goes under), and Best time of day (cloud cuts
  the light too).

The topic gate now admits "zebco" and "a/the/my fillet"; the Chinese and
Spanish glossaries gained the words their questions needed (保养, 换线, 扎手,
黑点, 放流的虹鳟; limpiar el carrete, cambiar el sedal, puntos negros). "Black
spots in my fillet" no longer reads as spotted bass ("spots"): a decoy
sentence and "fillet", "dots" and "parasite" as everyday words.

**Passage vectors are computed one passage at a time.** Measuring the new
cards against a copy of the code without them, answers that had nothing to
do with the new cards moved, and moved again after each small edit. The
cause: the int8 embedding model quantizes each run's activations on the fly,
so in a batch of 16 a passage's vector depended on the 15 passages beside
it. The same passage, embedded in two different batches, came out at cosine
0.997; adding any passage shifts every later batch, and answers near the
cut-off swapped places. Encoding one passage per run makes each vector
depend on its own text only, and is no slower: 625 passages take about 6
seconds, with no padding. The vector cache key now includes the encoding,
so vectors made in batches are never reused.

**A question set.** The 33 questions behind the new cards are
`eval/rag_cases.BOOKLET_CASES`, reported by `rag_runner`;
`tests/test_booklet_topics.py` pins the cards, the gate and glossary words,
and the encoding.

## Results

Served search (hybrid). The middle column is the old content with vectors
computed one at a time, which separates the effect of the encoding from the
effect of the new cards:

| | Before | One at a time, old content | After |
|---|---|---|---|
| Original set | 99.0% | 99.0% | 99.0% |
| Chinese | 100% | 100% | 100% |
| Rephrased | 96.5% | 98.2% | 98.2% |
| Untuned | 90.0% | 90.0% | 90.0% |
| New topics | 98.5% | 98.5% | 98.5% |
| Beginner questions | 68/69 | 67/69 | 67/69 |
| Booklet questions | 5/33 | 5/33 | 33/33 |

The encoding change gained one rephrased question and lost one beginner
question ("do I need a landing net"); the new cards then changed nothing
outside their own questions.

Keyword-only search (tests, CI): every set unchanged except the booklet
questions (5/33 to 29/33), new topics (+1, "my line keeps breaking when a
fish runs"), and the beginner questions (54/69 to 53/69: "湖里钓的鱼能吃吗"
falls from fourth to fifth).

New cards moved old answers down in three ways, each found by comparing
with the copy and fixed in the wording of the new card, not by relabelling:
a shared word that is rare in the corpus ("front" in "front cover" weakened
the cold-front card; "old", "year" and "least" in the line card caught "my
six year old"), a word that sounds like a fish ("spots"), and length (eight
long cards raised the average passage length that BM25 scores against, from
41.4 to 42.9 words; Best time of day needed its cloud sentence to stay ahead
of No bites for "is fishing better on cloudy days").

## Consequences

- The first Ask after deploy computes the passage vectors again (about 6 s
  locally), since the cache key changed; after that they are read from
  `models/multilingual-e5-small/passages-*.npy` as before.
- A before/after comparison on a copy now shows only what the change did.
  Before this, any edit added up to a place of noise near the cut-off.
- Muddy-tasting fish is still unwritten: no booklet explains it, and what
  was found is about farmed fish.
- Spanish questions are checked through `search_guides`, not the eval set,
  as in ADR 0049.
- The booklets' terms are in "Needs human review" 15.
