# ADR 0026: Names that are also everyday words, three honest empty answers, and a wider handbook

## Status
Accepted. Extends ADRs 0024 (the handbook) and 0025 (hybrid retrieval).

## Context

Three problems, all reported from use rather than found by the eval:

1. **A fish name that is also an everyday word.** ADR 0025 added a bare
   "bass" as the black basses, which made "what bass guitar strings should I
   buy" a fishing question. The same holds for "drum" (an instrument),
   "hybrid" (a car), "slab" (concrete), "whites" (laundry), "blues" (music),
   "spots" (places) and "cats" (pets). The nicknames anglers actually use
   were therefore either missing or dangerous.
2. **One "not covered" for three different situations.** "How do I bake
   sourdough bread", "how do I catch smallmouth bass" and "what is the world
   record bluegill" all got the same answer, which was misleading in the
   first two cases: the first was never searched, and the second is a real
   fish FishEye has no guide for.
3. **The handbook stopped at tackle and cleaning.** Nothing on casting, the
   drag, where fish hold, weather, safety, the licence, or cooking what you
   keep — all of which beginners ask about before they ask about a species.

## Decision

**An ambiguous name is resolved by comparison, not by a threshold.** Each
one gets `AmbiguousName` (retriever.py): the fish it would mean, plus decoy
sentences in its everyday sense ("A bass guitar, bass strings, playing bass
in a band, a bassist"). With the embedding model, the question is encoded
once and compared against that fish's own passages and against the decoys,
and the closer side wins. ADR 0025 found no cosine threshold could separate
fishing from everything else for this model; *which of two things a question
is closer to* is a different question, and the model answers it well.

Without the model the fallback is a rule, cruder on purpose: an everyday
word from the name's own list means the everyday sense; otherwise names that
are mostly fish in a fishing app ("slab", "whites") count as the fish, and
names that are mostly everyday words ("blues", "cats", "spots") need another
fishing word in the question.

Ambiguous names are matched only after the certain ones and after the fish
with no guide are blanked out, so "white bass", "freshwater drum" and
"smallmouth bass" never reach this path.

**Three empty answers instead of one** (`explain_empty`, Ask's `_empty`):
not read as a fishing question; a fish with no guide, named in the answer
("no guide for smallmouth bass yet"); or a fishing question the guides don't
answer. The trace carries which, and the badge says it.

**Twenty more handbook topics**, in four new categories — casting and
playing a fish (casting a spinning and a baitcasting reel, the drag,
measuring a fish, fishing from the bank, a first trip in Texas); weather,
water and where fish hold (cover, points and drop-offs, clarity and lure
colour, wind, fronts and pressure, cloud and sun); staying safe (life
jackets, handling a fish without getting hurt); and the licence, clean drain
dry, and old line — plus cooking, storing and freezing a catch under care.
Same rules as before: every sentence from a page that was opened, no limit
stated as a number, TPWD linked for the rules.

## Results (`python -m app.eval.rag_runner --compare`)

| | keyword only | hybrid |
|---|---|---|
| original set (98), hit@4 / MRR | 99% / 0.85 | 99% / 0.88 |
| Chinese (28), hit@4 | 100% | 96% |
| English paraphrases (15) | 60% | 73% |
| the new topics (34) | 85% | 100% |
| everyday-word names, both senses (33) | 94% | 100% |
| rephrased eval questions (50) | 90% | 96% |
| rephrased, written after tuning (30) | 77% | 90% |
| wrong-fish answers (80 rephrasings) | 1 | 1 |
| off-topic rejected (30 EN / 10 ZH) | 97% / 100% | 97% / 100% |
| fishing questions naming no fish, admitted | 100% | 100% |

The handbook is 64 topics (was 44), the index 294 passages (was 274), and
the sources 107 (was 92, 15 opened for this change).

"How do I cast farther", a known miss since ADR 0024, is now admitted and
answered with the casting topics, which is why unnamed-fishing admission
reaches 100%.

**Chinese gate.** "鱼" alone is not a fishing question (金鱼 is a goldfish,
鱼香 a flavour), so those senses are blanked out and "鱼" then counts like an
English ambiguous term, two of which are needed. "怎么给鱼保鲜" is now
answered; "鱼香肉丝怎么做" is still turned away.

## Consequences

- Chinese hit@4 fell from 100% to 96% with the model: "怎么让钓到的鱼保鲜带
  回家" now ranks the new freezing and storage topics above the labelled
  "keeping your catch fresh". All three answer the question, but the eval is
  strict and this is counted as a miss.
- The one remaining wrong-fish answer is a Texas-rig question that names no
  fish and draws in one unrelated setup passage at rank 4.
- Without the embedding model, "blues", "cats" and "spots" need another
  fishing word in the question, so "where do spots live" is turned away.
- `_SHARED_FIRST_WORDS` now covers safety and casting as well as rules: a
  question about the angler rather than the fish ("how do I hold a catfish
  without getting stabbed") leads with the handbook passage.
