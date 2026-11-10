"""How many pages were opened, which ones, and where from (services/visits.py).

    python -m app.cli.visits             # the last 30 days
    python -m app.cli.visits --days 7

On the server, from ~/FishEye:

    docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T backend python -m app.cli.visits

Counts only: nothing in them tells one visitor from another.
"""
from __future__ import annotations

import argparse

import app.models  # noqa: F401  (register every model)
from app.db.session import Base, SessionLocal, engine
from app.services import visits as svc


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args(argv)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        print(svc.as_text(svc.summary(db, max(1, args.days))))


if __name__ == "__main__":
    main()
