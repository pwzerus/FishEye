# ADR 0021: Request limits on the anonymous endpoints

## Status
Accepted.

## Context

Logins, registration, pin creation and reports already had limits
(ADR 0016). Everything a visitor can call without an account had none, and
several of those endpoints spend something that isn't ours:

- **Guide Q&A and the advisor** call a language model. With the mock that
  costs nothing; with a real model every request is billed.
- **Location search** proxies Nominatim, which allows this app one request a
  second in total (ADR 0009). The service queues requests to respect that,
  so one client sending a flood makes everyone else's search wait.
- **Weather and recommendations** call the National Weather Service for any
  place not cached in the last 15 minutes.
- **The map's lake queries** are database only, but they run on every pan
  and zoom, and will cover far more lakes once data goes beyond Texas.

Putting the site on a public address (docs/deploy-aws.md) is what makes this
matter: a script can call any of these in a loop.

Deploying also exposed a second problem. Behind Caddy, every request reaches
the backend from Caddy's address, so the existing login limits would have
counted the whole internet as one client: one person mistyping a password
forty times would lock everyone out of signing in.

## Decision

**Budgets per group of endpoints, per client IP, in process.**
`app/api/rate_limits.py` defines a `Budget` for each group and attaches it to
the routes as a FastAPI dependency, so a request over budget gets `429` with
`Retry-After` before the endpoint does any work.

| Budget | Endpoints | Per client | Everyone combined |
|---|---|---|---|
| `LLM` | `POST /api/ask`, `POST /api/advisor/explain` | 10 a minute, 100 a day | 2,000 a day |
| `GEOCODE` | `GET /api/geocode` | 20 a minute | |
| `WEATHER` | `GET /api/weather`, `POST /api/recommendations` | 60 a minute | |
| `MAP` | `/api/waterbodies` and its sub-routes | 300 a minute | |

- Endpoints in one group share one allowance, because they spend the same
  thing: asking the advisor uses up the same model budget as asking a
  question.
- The daily total on `LLM` is what bounds a real model's bill, however many
  addresses the requests come from. When it runs out the message says the
  AI features are done for the day and the rest of the site still works.
  It is a request count, not a spend cap in dollars; that comes with the
  real model.
- Every limit is checked before any is counted, so a refused request uses
  up nothing. Otherwise a client over its own limit could drain the shared
  daily total just by retrying.
- Not limited: health, the species guides and photos (static content and a
  cached upstream), states. The guide pages are server-rendered by the
  frontend container, so all of their API calls come from one address; a
  limit there would throttle the frontend, not a visitor.
- `RATE_LIMITS_ENABLED=false` turns all of this off, for an emergency.

**The client address behind the proxy.** In production uvicorn runs with
`FORWARDED_ALLOW_IPS="*"` (docker-compose.prod.yml), so it takes the
visitor's address from `X-Forwarded-For`. Trusting any sender is safe there
only because the backend's port is not published: just Caddy and the
frontend can reach it, and Caddy replaces any `X-Forwarded-For` a visitor
sends with the address the connection really came from. Verified with a real
uvicorn process: without the setting, a second visitor behind the same proxy
was refused after the first used up the allowance; with it, they were not.
The local compose file does not set it, because there the backend port is
published and anyone could claim any address.

**Memory.** `RateLimiter` used to forget a client only when that client came
back. With a one-day window and many one-off visitors that grows without
bound, so the limiter now prunes every key once the table passes a size, and
sets the next threshold to twice what remains.

**The frontend** shows the server's message on a 429 (Q&A, advisor and
location search) instead of "couldn't reach the server".

## Consequences

- Counts live in the one backend process. Several workers or servers would
  each count separately; that needs a shared store (Redis) and is not
  needed for one server.
- Counts reset on restart. Acceptable: the worst case is one extra
  allowance per restart.
- Many people behind one address (a campus, an office) share a limit. The
  per-client numbers are set well above what a person using the site does,
  so that should be rare.
- An attacker with many addresses gets many allowances. The daily total on
  the model endpoints is what still holds then; the others protect free
  services and are a nuisance limit, not a security boundary.
