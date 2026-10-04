# FishMate

<img src="docs/brand/fishmate-lockup.svg" alt="FishMate" width="280">


Map-based decision assistant for freshwater fishing beginners. Pick a lake and
a target species; the app turns scattered map, government, and weather data
into an explainable, executable fishing plan.

Full spec: see `docs/PRD.md` (written under the working name "FishPilot AI").

Status: in active development (portfolio project). See `docs/architecture/`
for system design and `docs/adr/` for engineering decisions.

## Quickstart

Needs Docker (Docker Desktop on Windows or macOS). No API keys.

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

This starts PostgreSQL with PostGIS, the API and the web app, and seeds three
demo lakes on first start. The fish guides and guide Q&A work right away; the
Q&A uses the built-in mock model (no key, no cost). Data is kept in Docker
volumes between runs; `docker compose down -v` wipes it and the next start
re-seeds.

Optional settings (map tiles, a real LLM, Google sign-in) go in a `.env` file
next to `docker-compose.yml`: `cp .env.example .env` and fill in what you
have. Compose reads it if it's there.

To load every named lake in Texas from OpenStreetMap (a few minutes, needs
network), run once while the stack is up:

```bash
docker compose exec backend python -m app.data_import.osm_waterbody_import --state TX
```

Running the backend and frontend directly, without Docker, is covered in
`backend/README.md` and `frontend/README.md`.

## Why this project exists

Built to demonstrate applied-AI + full-stack engineering judgment for
software/AI engineer roles: not just "call an LLM," but where an LLM is and
isn't the right tool, how to keep it honest with structured, source-grounded
output, and how to run the whole thing like a real service (evals,
observability, graceful degradation).

See `docs/architecture/decisions-summary.md` for the short version.
