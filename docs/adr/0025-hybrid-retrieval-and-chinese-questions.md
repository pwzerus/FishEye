# ADR 0025: Hybrid retrieval, Chinese questions, and "how do I fish for X"

## Status
Accepted. Adds an optional semantic ranker to Ask (ADRs 0014, 0023, 0024).
Keyword search stays, and stays the only thing that decides whether a
question is answered.

## Context

Keyword search (BM25 with species routing) did well on the eval questions,
which were written in the guides' own words, and badly on everything else:

- Chinese questions: 3 of 28 found the right passage, and only because a
  fish name happened to route them.
- English paraphrases that avoid the guides' words ("how do I stop my
  catch from going bad on a hot day"): 47%.
- Nicknames it didn't know sent questions to the wrong fish: "best bait for
  slabs" answered with white and striped bass, "what live bait do linesides
  want" with flathead catfish, the same failure as "what bait for bass" ->
  shad (ADR 0024 addendum).
- "How can I fish a bass" returned whichever four passages repeated "fish",
  not a plan.

## Decision

**Model.** intfloat/multilingual-e5-small (MIT, ~118M parameters,
multilingual, trained for query-to-passage search), run locally with
onnxruntime on the CPU and compressed to int8. Fetched once by
`python -m app.cli.fetch_embedding_model`, which pins the commit and checks
the license; the app never calls Hugging Face. Optional: without the model
or its packages (`requirements-semantic.txt`), Ask is keyword-only, as
before. `RAG_SEMANTIC=off|auto|on`.

**What the model may decide: ranking only.** Measured on this corpus, its
cosines are compressed and overlap: off-topic questions reach 0.885 against
the nearest passage, real Chinese fishing questions start at 0.757, and a
bass question scores 0.73 against a bread recipe. No threshold separates
them, so:

- the on-topic gate stays rule-based, with a Chinese word list added
  (`zh.FISHING_TERMS`: "钓" counts, "鱼" alone doesn't, because "鱼香肉丝"
  and "金鱼怎么养" aren't fishing questions);
- an English question keyword search finds nothing for is still "not
  covered" (the model always finds *something*);
- species routing, unguided fish ("smallmouth", "红鼓鱼") and the
  shared-passage rules are unchanged, now with about 50 Chinese fish names (and 22 Chinese names of unguided fish).

The model's top 5 passages (within the routed fish) are merged with the
keyword ranking by reciprocal rank fusion, at half the keyword ranking's
weight. Weight and depth were picked from 8 combinations on the eval.

**Chinese through a glossary as well.** `zh.with_english` appends the
English the guides use for about 100 Chinese terms (剥皮 -> skin, 放血 -> bleed,
帕洛马结 -> palomar knot). This alone took keyword search on Chinese from
11% to 100%; the model adds little on top for Chinese.

**"How do I fish for X".** A fish's name plus "catch/fish/tips" and nothing
narrower ("how can i fish a bass", "鲈鱼怎么钓", "teach me to catch a bass")
returns that fish's plan: bait, lures, the first rig, where and when. For a
family name the first fish (largemouth for "bass", channel for "catfish").

**Nicknames and phrasing found by rephrasing.** slab(s), bucketmouth, green
trout, sunnies, whiskerfish, catfishing, lineside(s); "X or Y" naming two
fish is an identification question; synonyms prepare, menu, edible, let.

## Results (`python -m app.eval.rag_runner --compare`, int8 model)

| | keyword only | hybrid |
|---|---|---|
| original set (98), hit@4 / MRR | 99% / 0.85 | 99% / 0.88 |
| Chinese (28), hit@4 | 100% | 100% |
| English paraphrases (15), hit@4 | 53% | 67% |
| rephrased eval questions (50), hit@4 | 90% | 96% |
| rephrased, written after tuning (30), hit@4 | 80% | 87% |
| wrong-fish answers (80 rephrasings) | 1 | 1 |
| off-topic rejected (30 EN / 10 ZH) | 97% / 100% | 97% / 100% |
| not covered (EN / ZH) | 100% / 100% | 100% / 100% |

The 50 rephrasings were used to find the nickname and synonym fixes, so
their number flatters; the 30 written afterwards were run once, before one
general fix ("teach me to catch a bass" -> the plan), and are the honest
estimate. Most of the gain on wrong-fish answers came from the rules, not
the model.

Cost: 118 MB on disk; the backend process uses about 450 MB with the model
(870 MB with the uncompressed one); about 3 ms per question on one CPU core.
Passage vectors are computed once and cached by content.

## Alternatives considered

- **Model as the gate.** Rejected on the cosine overlap above.
- **gte-multilingual-base.** Scores higher on public benchmarks, but about
  2.5x the size and needs `trust_remote_code`; the int8 e5-small fits the
  2 GB server.
- **A model rewriting the question first.** Would understand most, but costs
  a model call per question, against ADR 0023's "search is free".

## Consequences

- Still missed: questions with no fishing word at all ("how do I stop my
  catch from going bad on a hot day" is turned away by the gate), "blues"
  for blue catfish (also music), "spots" for spotted bass (also places).
- The Docker image doesn't include the model yet; a deployment without it
  runs keyword-only, which is now also good at Chinese.
- The trace shows "Keyword (BM25) + semantic" and fused scores (~0.01-0.03).
