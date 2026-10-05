# ADR 0007: AI advisor — keeping the model on facts it was given

## Context

PRD §5.1 asks for an LLM that explains the rule engine's spot ranking in
plain language. PRD constraint 1 says the LLM must not decide whether a
species is in a lake, invent regulations, or produce precise fishing spots;
constraint 3 says candidates come from explainable scoring and the LLM only
explains; constraint 7 says LLM output must be JSON validated server-side;
constraint 5 says weather warnings outrank fishing advice; constraint 14
asks for a per-request trace.

The obvious implementation — "put the facts in the system prompt, ask
nicely for JSON, parse it" — satisfies none of these as *guarantees*. A
system prompt is a request. The two failures that matter most here are
exactly the ones a prompt can't prevent, and both are silent:

- **A fabricated citation** makes an invented claim look sourced. Worse
  than an uncited claim, because it survives a skeptical reader's check.
- **A fabricated species** is constraint 1's explicit prohibition. "There
  are stripers in this lake" from a language model, shown next to real
  TPWD survey data, is indistinguishable from the real thing to a user.

## Decision

**1. Two grounding checks, run server-side on every response.**

- Every URL in `sources` must be one the backend supplied in the facts
  payload. Not a substring match, not a domain match — set membership.
- No species name in the model's prose may be one the system knows about
  but which is *not* confirmed for this lake. The vocabulary comes from the
  `species` table; the confirmed set comes from `waterbody_species`.

A response failing either check is **discarded entirely**, not repaired.
A model that fabricated one citation has told you something about the rest
of that answer, and patching out the bad field would leave the reasoning
that produced it in place.

The species check has a real limitation, documented at the function: it
relies on species names being distinctive enough not to collide with
ordinary fishing prose. Every current name is multi-word ("White Bass",
"Channel Catfish"), so "bring a bass rod" can't trip it; adding a bare
single-word species would start rejecting good answers. That's a constraint
on what may go in the `species` table, and the failure would be loud
(everything falls back) rather than silent.

**2. Safety warnings and confidence never pass through the model.**

They live at the top level of `AdvisorResponse`, outside `explanation`.
Constraint 5 is a guarantee, and a guarantee that depends on a model
choosing to repeat something isn't one — a model that omits the severe
thunderstorm warning from its `risks` array cannot suppress it, because the
warning was never in its hands. Same for confidence: the scoring engine
already computes it from which signals actually had data (ADR 0005's
partial-availability work). Asking a model to restate that number could
only make it wrong.

The schema encodes this. `AdvisorExplanationOut` has no field for
coordinates, species determinations, regulations, or confidence — the four
things constraint 1 prohibits — so there is nowhere for the model to put
them.

**3. A mock provider is a first-class provider, not a test fixture.**

`LLM_PROVIDER=mock` is the default and requires no key or spend. Three
reasons it's shipped rather than stubbed in tests:

- A reviewer can clone this repo and run the entire advisor flow in
  minutes. Same reasoning that chose Leaflet over the Google Maps JS API.
- PRD §11's demo script calls for *showing* the degradation path. You
  can't demo a fallback by hoping a real model misbehaves on cue.
  `LLM_MOCK_FAILURE_MODE` (`unavailable`, `invalid_json`,
  `hallucinated_source`, `hallucinated_species`) makes each failure
  reproducible on demand, from an env var, mid-demo.
- It keeps the pipeline honest. The mock answers using *only* the `<facts>`
  block in the prompt. If it can produce a complete answer, the prompt is
  genuinely self-contained — meaning a real model isn't being quietly
  relied on to supply facts from its weights. Constraint 1 enforced by
  construction rather than by instruction.

Mock output is always labelled (`provider: "mock"`, `answer_source`), the
same way the weather adapter labels its fallback. A UI that can't tell the
difference will eventually present one as the other.

**4. Retry once on bad output, don't retry an outage.**

A malformed or ungrounded answer gets one more attempt — models are
stochastic and a second sample often parses. A provider that declared
itself down (`LLMUnavailable`) is not retried at this layer: the provider
owns its own timeout/retry envelope, and a second immediate call to a
service that just failed only adds latency to a request that's already
going to fall back.

**5. The cache is keyed on the facts, not on (lake, species).**

A hash of the facts payload invalidates itself the moment anything the
answer depends on changes — new weather, a re-scored candidate, a newly
ingested species record — without the cache having to know which of those
moved. Fallback answers are deliberately *not* cached: one bad moment
shouldn't serve a degraded answer for the next 15 minutes.

**6. The trace is returned to the caller, not just logged.**

`trace_id`, provider, model, latency, tokens, estimated cost, validation
attempts, outcome, retrieved-source count, cache hit. For a portfolio
project the trace is the feature — being able to point at which path an
answer took is the difference between "it calls an LLM" and "it operates
one". `estimated_cost_usd` is named as an estimate because token pricing
isn't knowable in-process.

## Consequences

- A model outage, malformed output, or a rejected answer all still return
  **200** with a usable response. The ranking is valid without any prose
  attached; only the explanation degrades. `answer_source` and
  `trace.outcome` tell an honest caller exactly what happened.
- The grounding checks can't catch every fabrication — no static check can.
  They catch the two the PRD singles out. A claim like "fish the north
  bank at dawn" is unfalsifiable by this system and passes; that's a real
  residual risk, mitigated only by the fact that the prompt carries no
  information to invent such specifics from.
- No real provider is implemented yet. `LLM_PROVIDER=openai|anthropic`
  raises `NotImplementedError` rather than silently mocking, *except* when
  a provider is named but has no key — that logs and falls back to the
  mock, because a missing key is a deployment gap and taking the whole
  recommendation panel down over it helps nobody.
- Adding a real provider is one class implementing `complete()`. No policy
  lives in the provider layer, so the validation, retry, fallback, cache
  and trace behaviour is identical whichever vendor is plugged in.
