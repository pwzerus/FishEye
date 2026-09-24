# ADR 0008: A fixed eval harness for the AI advisor (PRD §15)

## Context

PRD §15 asks for at least: retrieval hit rate, citation correctness, factual
consistency, tool-call success rate, JSON compliance rate, p95 latency, and
per-request cost. ADR 0007 built the mechanism that makes citation- and
species-grounding a guarantee rather than a hope; this ADR is about proving
that mechanism actually works, on demand, rather than trusting a handful of
unit tests and a demo script to have exercised it.

Two things make a generic eval framework the wrong shape here:

- The advisor's entire premise is "don't trust the model" — a handful of
  hand-picked scenarios a person can read and agree are testing the right
  thing is worth more than broad statistical coverage of prompts nobody
  reviewed.
- Two of the PRD's named metrics don't have a literal referent in this
  system as built. Rather than compute a plausible-looking number for
  something that doesn't apply, the report says so.

## Decision

**A fixed list of 10 `EvalCase`s** (`app/eval/cases.py`), each declaring what
it's testing and what outcome/answer-source it expects:

- 2 happy-path cases (no species named; a confirmed species named).
- 4 edge cases that are real situations, not failures, and must still end in
  a validated answer: an *unconfirmed* species requested, stale/fallback
  weather, an active safety alert, a closed lake with nothing to rank.
- 4 adversarial cases, one per `MockProvider` failure mode from ADR 0007
  (`unavailable`, `invalid_json`, `hallucinated_source`,
  `hallucinated_species`), each expected to be caught and produce the fixed
  fallback.

Run against a small, hand-built database (`app/eval/fixtures.py`) — one open
lake with a confirmed species and a real access point, one closed lake with
zero access points — rather than the real TPWD-scraped data, so every case's
expectation is derivable by reading the fixture, not by knowing what the
scraper happened to return most recently.

**A genuine finding from building this, left in the suite rather than
smoothed over:** the "unconfirmed species requested" case was originally
written expecting a normal, validated answer (`ok`/`llm`) — after all, no
failure mode is injected, and "the fish you asked about isn't confirmed
here" is a legitimate thing to say. But the mock provider's honest phrasing
("X is the strongest option **for Peacock Bass** on this lake") asserts
presence of an unconfirmed species just by describing the request back —
and the grounding check correctly rejects it, same as it would a deliberate
hallucination. The case now expects exactly that (`ungrounded_species` /
`fallback`), with a comment explaining why. This is arguably a *stronger*
proof of constraint 1 than the adversarial case alone: it shows the
guardrail also fires in ordinary use, not only under a simulated attack —
though it's also a real product question worth flagging: a user who asks
about a species this lake doesn't have currently gets the generic "nothing
to add" fallback rather than an explicit "not confirmed here" answer. Fine
for now; worth revisiting if a real provider's phrasing differs from the
mock's.

**Metrics (`app/eval/metrics.py`) map onto PRD §15 as follows:**

| PRD §15 asks for | This reports | Why |
|---|---|---|
| retrieval hit rate | `retrieval_hit_rate` — fraction of non-adversarial cases whose gathered facts actually carried sources + species evidence | Adversarial cases are excluded: they test the *model's* output, not whether retrieval found data |
| citation correctness | `citation_and_factual_consistency_note` (prose) + `adversarial_catch_rate` | `parse_and_validate()` rejects any answer citing an unsupplied source, so correctness is 100% by construction on every accepted answer — the number that can actually fail is whether the four hallucination cases were caught |
| factual consistency | same as above | Same reasoning, for the species-grounding check |
| tool-call success rate | `tool_call_success_rate_note` (prose) + `fallback_rate_overall` / `fallback_rate_happy_path` | Presumes the §13 tool-calling agent path, which was never built (§5.1's RAG-explanation path was built first, by explicit project choice). `fallback_rate_happy_path` — which must be 0% — is the closest analog: how often the *ordinary* path degraded |
| JSON compliance rate | `json_compliance_rate` — fraction of cases ending in `OUTCOME_OK` | Direct |
| p95 latency | `p95_latency_ms` (also reports p50) | Nearest-rank percentile — a fitted/interpolated percentile would imply more precision than a ~10-case suite has |
| per-request cost | `total_cost_usd`, `avg_cost_usd` | Direct from each trace's `estimated_cost_usd`; against the mock provider these are $0 by construction, so this number is validated by shape, not value, until a real provider exists |

**Run it:**

```
python -m app.eval.runner            # table + summary
python -m app.eval.runner --json     # machine-readable, same fields
```

Exit code is 0 only if every case passed, so it can gate CI later without
anyone having to read the output.

**`tests/test_eval.py`** covers two levels: the metrics arithmetic against
synthetic results (so the math is checked independent of the advisor
running), and an end-to-end run of the real case list — the one that would
actually catch a regression, e.g. a future change to `ai_advisor.py` that
let a fabricated citation slip past validation.

## Consequences

- The eval suite runs entirely against `MockProvider`. It proves the
  *pipeline* — grounding, retry, fallback, trace — behaves correctly under
  every failure mode the mock can simulate. It does not and cannot prove
  anything about a real model's behavior, phrasing quality, or actual
  hallucination rate, because no real provider is implemented yet (ADR
  0007). Re-running this suite against a real provider once one exists
  would be a meaningful next check, not a formality.
- 10 fixed cases is deliberately small. It is not a statistical sample of
  possible inputs — it is a checklist of the specific behaviors the PRD's
  hard constraints require, written so a reviewer can read `cases.py` and
  audit the eval suite itself as easily as the code it's testing.
- The "not applicable" notes for tool-call success rate are printed in every
  report, not just documented here, so a future reader of the eval output
  alone (without this ADR open) still gets the caveat rather than a
  number that quietly means something different than the PRD's term.
