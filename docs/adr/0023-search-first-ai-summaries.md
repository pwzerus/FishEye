# ADR 0023: Search the guides first; AI summaries on request, per account

## Status
Accepted. Changes how guide Q&A (ADR 0014) is served; ADR 0021's model
budget stays as the backstop behind it.

## Context

Every question on the Ask page called the language model. That made the
model the product, when what actually answers a beginner's question is the
reviewed guide passage, and the model only restates it in a few sentences
(the validator in services/rag/ask.py exists to make sure it does nothing
more). It also made every visitor's question a billed request, bounded only
by per-address limits (ADR 0021) that anyone can step around by changing
address.

Measuring the question the model was gated on exposed a second problem. A
question that names no fish was searched if it contained any word from a
list of "fishing words", and the list mixed real fishing words with
everyday ones: `where`, `when`, `time`, `easy`, `legal`, `line`, `tie`,
`boat`, `eat`. Of 21 off-topic questions written to probe it, 14 were
searched as fishing questions, among them "where is the nearest hospital",
"how to tie a tie" (which outscored a real knot question) and "what do
sharks eat". The original 3-question off-topic set had passed at 100%.

## Decision

**Two steps.**

1. `POST /api/ask` searches the guides and returns the passages, with their
   sources. No model, no account, nothing billed. This is what everyone sees
   first.
2. `POST /api/ask/summary` has the model write an answer from those same
   passages, through the existing validator. It needs an account and is
   limited to `AI_SUMMARIES_PER_DAY` (3) per account per UTC day. Admins are
   not limited.

**Per account, not per browser or address.** An address is shared by
everyone behind one office network (one interviewer would use up a whole
company's allowance) and a browser forgets on a cleared cache. An account
is the one thing that is both individual and costs the visitor something
to multiply.

**What counts.** A summary is reserved before the model is called, with a
single conditional `UPDATE ... WHERE used < limit`, so two requests at the
same moment can't both take the last one. It is given back when no
model-written answer comes of it (the model was unreachable, or its answer
failed validation and the passages were quoted instead), and when the answer
came from the cache, which cost nothing.

**Only fishing questions reach the model.** The summary endpoint runs the
search first; a question that retrieves nothing is refused (422) before a
summary is reserved. The gate it relies on was rebuilt:

- One *fishing* word is enough: fish, fishing, bait, lure, rod, reel,
  tackle, hook, bobber, jig and similar.
- *Ambiguous* words (line, tie, boat, lake, eat, feed, deep, cast, ...)
  count only in pairs: "hook and line", "worms off the bank".
- Question words (where, when, easy, legal) never count.
- The gate reads the raw question. "fish", "fishing" and "catch" are
  stopwords for ranking, so the old gate, which read the ranking tokens,
  never saw the words that most clearly say a question is about fishing.

A score threshold was tried first and doesn't work here: "how to tie a tie"
scored 6.94 against the guides and "how do I tie a fishing knot" 3.47, so no
threshold separates them.

## Result

The eval (app/eval/rag_cases.py) gained the 21 probe questions and a second
measure, fishing questions that name no fish, which only the gate decides:

| | before | after |
|---|---|---|
| off-topic questions searched | 14 of 24 | 1 of 24 |
| unnamed fishing questions admitted | 14 of 15 | 14 of 15 |
| hit@4 on the 36 answerable questions | 97% | 97% |

The one off-topic question still searched is "recommend a hook for my
song": counting "hook" as a fishing word is what lets "what size hook
should I use" through, and the beginner's question matters more. The one
fishing question turned away is "how do I cast farther" (only one
ambiguous word). Both are reported by the eval rather than reworded away;
an embedding retriever (the seam ADR 0014 left) is the next thing to measure
against them.

## Consequences

- The Ask page works fully signed out; the summary is an extra. A model
  outage, an exhausted daily cap or a missing key now cost a visitor a
  paraphrase, not the answer.
- The per-account allowance sits inside ADR 0021's limits, which still
  apply: the per-address minute and day limits, and the daily total across
  everyone that bounds the bill.
- The advisor's model call (`/api/advisor/explain`) is unchanged: anonymous,
  under ADR 0021's limits only.
- One more table, `ai_usage` (account, day, used), created by `create_all`
  like every other; there are no migrations to run.
- Counting by UTC day means the allowance resets at 7 pm in Texas in summer
  and 6 pm in winter.
