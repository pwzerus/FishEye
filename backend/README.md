# Backend — FastAPI

## Local dev (without Docker)

macOS/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# seed 3 demo lakes into a local sqlite db
DATABASE_URL=sqlite:///./fishpilot_dev.db python -m app.data_import.seed_tx_lakes

DATABASE_URL=sqlite:///./fishpilot_dev.db uvicorn app.main:app --reload
```

Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:DATABASE_URL="sqlite:///./fishpilot_dev.db"
python -m app.data_import.seed_tx_lakes
uvicorn app.main:app --reload
```

`requirements.txt` intentionally does **not** include `psycopg2-binary` —
local dev defaults to SQLite (see ADR 0001), and `psycopg2-binary` has no
prebuilt wheel for every Python/OS combination (notably Python 3.13 on
Windows), where pip falls back to compiling from source and fails without a
C++ toolchain installed. Only install it if you're actually pointing
`DATABASE_URL` at a real Postgres instance:
```
pip install -r requirements-postgres.txt
```

### Loading the data

Run these in order (Windows PowerShell shown; set `DATABASE_URL` as above):

```powershell
python -m app.data_import.seed_tx_lakes                    # 3 demo lakes
python -m app.data_import.tpwd_lake_survey_scraper         # TPWD-verified lakes (needs network)
python -m app.data_import.osm_waterbody_import --state TX --save-raw tx_osm.json
python -m app.data_import.gbif_occurrence_import --osm tx_osm.json --save-raw gbif_tx_raw.json
```

The OSM import pulls every named lake and reservoir in Texas, plus public boat
ramps and fishing piers, from OpenStreetMap's Overpass API. It can take a few
minutes. `--save-raw` keeps the response so you can re-run offline with
`--from-file tx_osm.json`. These lakes are shown as unverified: see
`docs/adr/0010-statewide-osm-layer.md`.

The GBIF import attaches species records (museum specimens, surveys,
iNaturalist) to those lakes, shown as "reported", never as confirmed:
see `docs/adr/0012-gbif-reported-species.md`. It downloads about 130,000
records (a few minutes); `--from-file gbif_tx_raw.json` re-runs offline.
Run it again after every OSM import.

There are no schema migrations yet. New *tables* are created automatically
when the API starts. After pulling model changes that add *columns*, delete
`fishpilot_dev.db` and run the commands again.

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
