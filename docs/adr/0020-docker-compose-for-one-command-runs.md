# ADR 0020: Docker Compose for one-command runs

## Status
Accepted.

## Context

The README promised `docker compose up --build`, but there was no compose
file and no Dockerfile. Running the app meant a Python virtualenv, a Node
install, a seed script and two terminals, with the backend on SQLite. That
is fine for development and poor for anyone trying the project from a clean
clone, and it never exercised the PostgreSQL + PostGIS path that a
deployment uses (ADR 0018).

## Decision

`docker-compose.yml` at the repo root runs three services:

- **db**: `postgis/postgis:16-3.4`. Its port is not published, so its
  local-only password is reachable only by the other containers. Data is in
  a named volume.
- **backend**: `python:3.11-slim`, non-root user. On start it runs the
  existing seed script (three demo lakes; a no-op once data exists), then
  uvicorn. Uploaded photos go to a second named volume. Compose overrides
  `DATABASE_URL` and `MEDIA_ROOT`, so a `.env` written for running the
  backend directly (SQLite, `./media`) still works.
- **frontend**: Next.js `output: "standalone"`, built in three stages so the
  runtime image has no build toolchain; non-root user.

Nothing needs a key: the LLM is the mock provider, weather is NWS, and the
map falls back to OpenStreetMap tiles. `.env` is optional.

Two problems only showed up once the frontend ran in its own container:

1. **Server-side fetches used the browser's URL.** Server components called
   `NEXT_PUBLIC_API_BASE_URL` (`localhost:8000`), which inside the frontend
   container is the frontend itself. `lib/api/client.ts` now uses
   `API_INTERNAL_URL` on the server when it is set (`http://backend:8000` in
   compose) and the public URL in the browser. The variable has no
   `NEXT_PUBLIC_` prefix, so it is read at run time and never reaches the
   bundle. Unset, nothing changes.
2. **Pages prerendered during the image build baked in "backend
   unreachable".** `/`, `/fish` and `/map` were static with a 30-second
   revalidate, and `next build` runs before any backend exists, so the
   first visitor after every start got the error fallback. These three pages
   are now rendered per request (`dynamic = "force-dynamic"`). Their API
   calls still cache for 30 seconds, so the backend sees about the same load.
   The same would have hit any CI or hosted build made without the API
   running.

A third was in `.env.example`: Compose reads `KEY=   # note` as the value
`# note`, so three empty keys (Google Places, LLM key, LLM model) would have
been set to their comments. The comments now sit on their own lines.

## Verified

The container registry was unreachable from the environment this was
written in, so the images could not be built there. The steps inside them
were checked without Docker, against the same versions:
PostgreSQL 16 + PostGIS 3.4, Python 3.11 with only `requirements.txt`, the
seed and restart (second start skips the seed), a 40 km PostGIS radius
query, guide Q&A, and the standalone Next server built with an unreachable
public API URL, so the pages could only get data through
`API_INTERNAL_URL`. Every page had data on its first request. Backend tests
(425) and frontend tests (160) pass.

## Not covered

- Deployment. This is for running locally; the AWS plan (EC2 + RDS + S3)
  reuses the images but not this file.
- The statewide OSM and GBIF imports stay manual (see README); they take
  minutes and need network, which a first start shouldn't depend on.
- `requirements.txt` still includes the test and lint tools, so they are in
  the backend image. Splitting dev dependencies out is a small follow-up.
