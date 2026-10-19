# ADR 0024: An angler's handbook, six more fish, and wider guide sections

## Status
Accepted. Extends the species guides (ADR 0014) and the search-first Ask
page (ADR 0023). Retrieval stays BM25 with species routing.

## Context

Ask could answer "what bait for crappie" and "how do I tell white bass from
hybrid striped bass", because the twelve guides covered identification,
where and when, bait, lures and tackle. It could not answer most of what
beginners actually ask next: how to clean or fillet a fish, how to kill one
humanely, whether it's safe to eat, why a bait works, what a palomar knot or
a slip bobber is, what a fish likes and where it lives, or anything about
flathead catfish, carp, drum, rainbow trout, redear or Guadalupe bass. Those
questions either came back "not covered" or matched the wrong section.

The on-topic gate also didn't know most bait, lure and tackle names, so
"what is split shot" or "how do I use a circle hook" were turned away before
they were searched.

## Decision

**A shared handbook.** `app/knowledge/angling_handbook.py` holds 44 topics in
seven categories that apply to every fish: live and natural baits (worms,
minnows, insects, grubs, crayfish, shad and cut bait, liver, stink bait,
dough and corn, shrimp), lures (soft plastics, crankbaits, spinnerbaits,
spoons, topwater), tackle (reels, rods, line, hooks, circle hooks, split
shot, sinkers, bobbers, leaders), knots (improved clinch, palomar, arbor),
care and cleaning (release, keeping a catch, dispatching and bleeding,
scaling, filleting, panfish, skinning catfish, the filleting rule, eating
safely), identification across families (catfish, black bass, temperate
bass, panfish, shad, others) and timing (time of day, season). Each topic is
one passage, cited as `/fish#<topic-id>` and shown as a card on `/fish`.

**Four more sections per guide.** `habitat`, `habits` (feeding, schooling,
spawning, temperature), `why_these_baits` (why the guide's baits work, not
just which) and `eating` (cleaning and table quality). Every guide has the
first three; `eating` where a source covers it.

**Six more fish**, each a full guide with setups: flathead catfish,
Guadalupe bass, redear sunfish, rainbow trout, freshwater drum, common carp.

**Same sourcing rules as ADR 0014.** Every sentence comes from a page that
was opened and read (TPWD first, then Texas A&M AgriLife, other state
agencies and established fishing publications); claims that couldn't be
traced to a page were cut. No limit is stated as a number; regulations link
to TPWD. Tests enforce both (`tests/test_handbook.py`).

**Retrieval changes.** The gate learned bait, lure, tackle and knot names
(one suffices), plus words that are fishing only in context (`corn`,
`spoon`, `fillet`, `clean`, `release`: two needed) and phrases (`split shot`,
`circle hook`, `catch and release`, `texas rig`). New synonyms map how
beginners ask (`gut`, `kill`, `vs`, `advantage`, `taste`) onto how the
passages are written. Single-letter tokens are dropped (the `s` of "what's"
was matching possessives), "why" is no longer a stopword, and "is it good to
eat" is routed to the eating section rather than the diet in `habits`.

## Alternatives considered

- **Put the shared material into every species guide.** Cleaning, knots and
  tackle would be repeated eighteen times, each copy a passage competing for
  the same four slots. One handbook passage, interleaved after the species
  passages, answers them once.
- **Let the model answer from general knowledge when no passage matches.**
  Rejected for the reason ADR 0014 gives: the answer couldn't be cited or
  reviewed, and "not covered" is the honest reply.
- **Embeddings now.** The misses the new eval found were vocabulary (the
  gate didn't know "split shot"; "gut" wasn't "clean"), which synonyms and
  the term lists fix cheaply and testably. Paraphrase misses are what would
  justify embeddings, and the eval doesn't show many yet.

## Results (`python -m app.eval.rag_runner`)

| | before | after |
|---|---|---|
| passages | ~110 | 274 |
| guides | 12 | 18 |
| eval questions | 36 | 95 |
| hit@4 | 97% | 99% |
| MRR | 0.87 | 0.85 |
| off-topic rejected | 20/21 | 29/30 |
| fishing questions naming no fish admitted | 14/15 | 20/21 |
| not covered rejected | 100% | 100% |

On the original 36 questions alone, hit@4 is unchanged and MRR fell from
0.87 to 0.83: with more passages, three answers moved down a place or two
("can I bring live bait from one lake to another" now ranks white
bass's *why these baits* first). That is a real, small loss, kept because the right passage still
lands in the top four.

## Consequences

- Known misses: "how do I cast farther" is turned away (no casting topic),
  "recommend a hook for my song" is searched, and the blue catfish bait
  question still misses (it did before).
- The six new species have no curated photos yet
  (`species_photos.AWAITING_CURATION`); their pages use the drawn art.
- The TPWD importer's `KNOWN_SPECIES` is unchanged, so lake pages don't link
  to the new guides yet.
- The next retrieval step is still hybrid search (ADR 0023's roadmap), now
  with a larger eval set to judge it.

## Addendum: a bare "bass"

Reported after release: "how to catch bass, what kind of bait should I use"
answered with the gizzard and threadfin shad bait lists. "Bass" alone was
not a recognised name, so the question searched every passage, and the shad
passages repeat "striped bass and hybrid striped bass". Now:

- A bare "bass" (or "black bass") routes to the three black basses, as in
  TPWD's usage. Longer names ("white bass", "striped bass") still match
  first, and "bass" followed by an instrument word ("bass guitar") is not
  a fish.
- Fish without a guide whose names contain a guided fish's name
  (`UNGUIDED_FISH`: "smallmouth bass", "red drum", "speckled trout",
  "yellow perch", ...) are blanked out before names are matched, and a
  question naming only those gets "not covered" rather than whatever
  passages share the word.
- A routed question that asks whether something is legal leads with the
  best shared passage, because statewide rules live there ("is it legal to
  use a small bass as bait").

Three questions were added to the eval and three to not-covered (98 in
all): hit@4 99%, MRR 0.85, unchanged on the previous 95.
