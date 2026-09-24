# FishMate

<img src="docs/brand/fishmate-lockup.svg" alt="FishMate" width="280">


Map-based decision assistant for freshwater fishing beginners. Pick a lake and
a target species; the app turns scattered map, government, and weather data
into an explainable, executable fishing plan.

Full spec: see `docs/PRD.md` (written under the working name "FishPilot AI").

Status: in active development (portfolio project). See `docs/architecture/`
for system design and `docs/adr/` for engineering decisions.

## Quickstart

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/docs

## Why this project exists

Built to demonstrate applied-AI + full-stack engineering judgment for
software/AI engineer roles: not just "call an LLM," but where an LLM is and
isn't the right tool, how to keep it honest with structured, source-grounded
output, and how to run the whole thing like a real service (evals,
observability, graceful degradation).

See `docs/architecture/decisions-summary.md` for the short version.
