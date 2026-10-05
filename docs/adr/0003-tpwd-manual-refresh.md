# ADR 0003: Manual TPWD-refresh trigger, admin-gated, not a scheduled job

## Status
Accepted

## Context
The TPWD scraper (ADR 0002) works, but "every 3-7 days, automatically" —
the original ask — turned out to be blocked by infrastructure outside
this project's control: every environment Claude can run code in (the
cloud sandbox used during development, and the device-bridge VM used to
reach the developer's own machine) sits behind an account-level network
egress allowlist that blocks `tpwd.texas.gov` entirely. That's not a bug
in this project; it's a property of the tooling used to build it, and it
doesn't apply once this backend is actually deployed or run from a
normal machine with unrestricted internet.

A real scheduled job (cron / Windows Task Scheduler / a cloud scheduler)
is still the right answer for "runs automatically, unattended," and
remains a known gap (see ADR 0002). This ADR covers a complementary,
immediately useful piece: a **manual trigger** — a button that starts a
refresh on demand, so a run doesn't require SSH-ing in and typing a CLI
command every time.

## Decision

### 1. A backend API endpoint, not a browser-side scraper
The obvious-looking alternative — have each visitor's browser fetch and
parse the TPWD pages directly — doesn't work and wouldn't be safe if it
did:
- TPWD's server doesn't send CORS headers permitting cross-origin
  `fetch()` from an arbitrary frontend origin; the browser blocks it
  before the request even completes.
- BeautifulSoup-style parsing and the SQLAlchemy writes have to happen
  somewhere with server-side Python and DB access — a browser tab can't
  do either.
- Trusting whatever an anonymous visitor's browser claims to have
  scraped, and writing that into the shared database, would be a real
  data-integrity hole — anyone could inject fabricated species records.
  That's the opposite of ADR 0002's whole premise (every fact traceable
  to an exact source sentence, `confidence` tiers meaning something).

So the button calls this backend's own API, which runs the same
`tpwd_lake_survey_scraper.run()` used by the CLI. Wherever this backend
is actually hosted — a real cloud host, or just the developer's own
machine — that's a normal network with no egress restriction, so the
scraper's live HTTP calls work the same way they did in the developer's
own manual dry-run test.

### 2. Background task, not a blocking request
The scraper takes roughly 15 seconds for 7 lakes (2s politeness delay
between each, per ADR 0002 §5). A synchronous endpoint would hang the
HTTP request for that whole time. Instead:
- `POST /api/admin/tpwd-refresh` starts the job via FastAPI
  `BackgroundTasks` and returns `202 Accepted` immediately.
- `GET /api/admin/tpwd-refresh/status` reports `idle` / `running` /
  `done` / `error`, plus the last run's per-lake results once finished.
- The frontend button polls the status endpoint rather than waiting on
  the trigger call.

`tpwd_lake_survey_scraper.run()` was refactored to return a structured
`IngestSummary` (list of per-lake `LakeResult`s + total written) instead
of only printing, so the API layer can report real results without
scraping stdout.

### 3. One job at a time, tracked in-memory
`app/services/tpwd_refresh_job.py` is a single in-memory job-state
singleton guarded by a lock — not a real task queue (Celery/RQ/etc.). A
second trigger while one is running gets `409 Conflict` rather than
being queued. This is an explicit, disclosed shortcut appropriate to a
single-process portfolio demo with one operator; a real multi-worker
deployment would need a shared store (DB row, Redis) instead, since
in-memory state doesn't survive a process restart or exist across
workers.

### 4. Gated by a single shared token, not a real auth system
`Settings.admin_api_token` (env-configured, no default — see
`app/core/config.py`) is checked via an `X-Admin-Token` header on both
endpoints. If the token isn't configured, the endpoint returns `503`
rather than silently allowing unauthenticated access — a missing secret
must never widen access. This is intentionally not a full user-accounts
system: there's exactly one operator (the developer) for this demo. A
real multi-operator deployment would need per-user auth, rate limiting,
and audit logging of who triggered what and when.

## Consequences
- The "every 3-7 days automatically" goal from the original ask is
  *not* solved by this ADR — that still needs a real scheduler running
  somewhere with a normal network connection (see ADR 0002's known
  gaps). This ADR solves the more immediately useful "trigger it without
  opening a terminal" problem.
- The admin endpoint's shortcuts (single shared token, in-memory job
  state, no rate limiting) are fine for a demo but are explicitly listed
  here so they're not mistaken for production-ready design if this ever
  needs to serve more than one operator.
