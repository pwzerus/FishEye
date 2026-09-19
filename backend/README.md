# Backend — FastAPI

## Local dev (without Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# seed 3 demo lakes into a local sqlite db
DATABASE_URL=sqlite:///./fishpilot_dev.db python -m app.data_import.seed_tx_lakes

DATABASE_URL=sqlite:///./fishpilot_dev.db uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## Tests

```bash
source .venv/bin/activate
PYTHONPATH=. pytest -v
```

Tests run against an in-memory SQLite DB (see `tests/conftest.py`) — no
external services or Docker required. This is deliberate: nothing in the
domain layer (models, scoring, API routing) should require Postgres-specific
features, so CI stays fast and anyone cloning the repo can run tests with
zero setup.

## Layout

- `app/models/` — SQLAlchemy ORM models (source of truth for schema)
- `app/schemas/` — Pydantic request/response models (API contract, separate
  from the DB models on purpose — the API shape and the storage shape are
  allowed to diverge)
- `app/api/` — route handlers, one router per resource
- `app/services/` — business logic that isn't just "read the DB" (geo math
  today; weather adapter, scoring engine, AI advisor land in later branches)
- `app/data_import/` — one-off/seed data scripts, not part of the request path
