"""PRD §15 eval harness for the AI advisor.

This is deliberately not a general-purpose eval framework: it is a small,
fixed set of scenarios (see cases.py) run against the mock provider, scored
against what each scenario is *supposed* to do, and rolled up into the
metrics PRD §15 asks for (metrics.py). Run it with:

    python -m app.eval.runner

See docs/adr/0008-eval-harness.md for what each metric means here and,
importantly, where the PRD's metric doesn't map cleanly onto what this
system actually does (the tool-calling agent path in §13 was never built,
so "tool-call success rate" has no literal referent — the report says so
rather than inventing a number for it).
"""
