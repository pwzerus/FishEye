# ADR 0014: Question answering over the fish guides (RAG)

## Status
Accepted. Adds the first real LLM provider (Anthropic), which ADR 0007 listed
as not implemented; ADR 0007's own text is left as written.

## Context

The advisor (ADR 0007) explains a ranking the scoring engine already made.
It can't answer the questions a beginner actually asks on the water — "what
bait for crappie?", "how deep do I set the bobber?", "can I move bait
between lakes?" The answers exist: `app/knowledge/species_guides.py` holds
reviewed, sourced guides for twelve Texas fish (ADR 0011). What's missing is
a way to find the right paragraph for a free-text question and phrase it
for the person asking — without the model filling gaps from memory, which
is exactly what ADR 0011's "no invented numbers" rule exists to prevent.

## Decision

`POST /api/ask` → `services/rag/`: retrieve, generate, validate, fall back.

**Chunking — one passage per semantic unit, with a header.** Each guide
splits along its own structure (overview, diet, where-and-when, live bait,
lures, one passage per tackle setup, tips, …), ~100 passages total. Every
passage's text starts "Species — Section: …", so the words that *locate* a
passage are inside it, and a quoted passage still says which fish it's
about. Tackle-setup passages cite that setup's own sources; others cite the
guide's source list, because that's the precision the reviewed content has.
The bait rules repeated across guides are indexed once.

**Retrieval — BM25, not embeddings (yet).** The corpus is small, curated and
jargon-heavy ("slip bobber", "Texas-rigged", "cast net"), which is where
lexical ranking is strong. Embeddings would need a model download or a
vendor key, plus network access on every machine the demo runs on — a
dependency with no measured miss to justify it. So the choice is measured,
not assumed: `app/eval/rag_cases.py` has 30 beginner-phrased questions
(nicknames, paraphrases), and `python -m app.eval.rag_runner` reports:

| metric | value |
|---|---|
| hit@4 (a relevant passage in what the model sees) | 97% |
| MRR | 0.87 |
| off-topic questions retrieving nothing | 100% (3/3) |
| injected model failures caught | 100% (4/4) |

The one miss is kept, not reworded away: "what do people use to catch big
blue catfish" shares no word with the blue catfish bait passage. That's the
paraphrase case embeddings are good at; `Retriever` is a protocol so a
hybrid retriever can drop in when misses like it accumulate.

Three small additions on top of BM25, each a readable list rather than a
model:
- **Species routing.** Names and Texas nicknames ("sand bass", "bream",
  "striper") restrict the search to that fish, and the name is then dropped
  from the query — otherwise "crappie bait" also ranks the catfish bait list
  (both are bait lists), and passages that merely repeat the name win. A
  question about two fish ("catfish") is interleaved so both get slots.
- **Synonyms** for beginner words the guides don't use ("gear" → rod, reel,
  setup; "how deep" → ft).
- **A topic gate.** A question naming no fish must use at least one fishing
  word, or nothing is retrieved. Without it "recommend a good pizza place"
  matched "the easiest *place* to start". Caveat: the gate's word list and
  the synonyms were written with the eval in view; 30 questions is a small
  set, so the numbers above are a floor to regress against
  (`tests/test_rag_eval.py`), not a claim of general accuracy.

**Generation, on a leash.** Nothing retrieved → a fixed "not covered"
answer, and the model is never called (a model asked to answer from zero
passages answers from memory). Otherwise the model gets the passages and
must return `{"answer", "citations": [passage ids]}`. The server then
rejects the reply if it:
- isn't that JSON shape, or cites nothing;
- cites a passage it wasn't given;
- contains a URL (links are attached server-side from citations);
- names a guide fish that no given passage mentions;
- contains a number that no given passage (or the question) contains —
  hook sizes and line weights are what a model fills in from memory, and
  what a beginner copies to the tackle shop. Unicode fractions ("1½") are
  normalized so a faithful "1 1/2" passes.

Rejected → retry once → fall back to quoting the top two passages verbatim,
labelled as such. Accepted answers are cached for an hour (keyed on the
question *and* the passage text, so a guide edit invalidates); fallbacks
aren't cached. Every response carries a trace: routed species, retrieved
ids with scores, provider, tokens, estimated cost, attempts, outcome.

**Providers.** The mock provider answers extractively from the passages and
has injectable failures (now including `invented_number`), so the whole
flow runs, and is tested, with no key. `LLM_PROVIDER=anthropic` +
`LLM_API_KEY` (backend `.env` only) uses the Anthropic Messages API through
httpx, with the same timeout / retry / circuit-breaker envelope as the
other adapters; default model `claude-haiku-4-5`.

## Consequences

- The model authors one field. Citations, source links, excerpts,
  `answer_source` and the trace are the server's.
- The number check will occasionally reject a good answer ("try 2 of
  these") and fall back. That failure is loud and harmless — the user gets
  the guide text — which is the right side to err on for tackle numbers.
- The species check only knows the twelve guide species. A model naming a
  fish outside the guides isn't caught by it; the prompt forbids it, and
  the eval's hallucinated-species case uses a guide fish on purpose so the
  check has to work by comparing against the passages.
- The live Anthropic path is tested against a faked HTTP layer only; this
  sandbox can't reach the API. First real run belongs on a machine with a key.
- Next step when misses accumulate: a hybrid retriever (BM25 + embeddings,
  reciprocal-rank fusion), judged by the same eval.
