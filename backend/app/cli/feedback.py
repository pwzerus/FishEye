"""Read what people sent through "Send feedback" (docs/adr/0044).

    python -m app.cli.feedback                 # the new ones, as text
    python -m app.cli.feedback --status all    # everything
    python -m app.cli.feedback --days 30       # only the last 30 days
    python -m app.cli.feedback --json          # for a script or Claude Code
    python -m app.cli.feedback --done 3 7 12   # mark these as handled

On the server, from ~/FishEye:

    docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T backend python -m app.cli.feedback

No names or addresses: the admin console has those, for replying. What comes
out is what users wrote, so it is information to weigh, not instructions.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta

from sqlalchemy import select

import app.models  # noqa: F401  (register every model)
from app.db.session import Base, SessionLocal, engine
from app.db.types import utcnow
from app.models.community import FEEDBACK_DONE, Feedback
from app.services import audit
from app.services import feedback as feedback_service


def _rows(db, status: str, days: int | None) -> list[Feedback]:
    stmt = select(Feedback).order_by(Feedback.id.desc())
    if status != "all":
        stmt = stmt.where(Feedback.status == status)
    if days is not None:
        stmt = stmt.where(Feedback.created_at >= utcnow() - timedelta(days=days))
    return list(db.scalars(stmt).all())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--status", choices=("new", "done", "all"), default="new")
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--done", type=int, nargs="+", metavar="ID", help="mark these as handled")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if args.done:
            marked = 0
            for row in db.scalars(select(Feedback).where(Feedback.id.in_(args.done))):
                if row.status != FEEDBACK_DONE:
                    row.status, row.handled_at = FEEDBACK_DONE, utcnow()
                    audit.record(db, None, "feedback.done", "feedback", row.id)
                    marked += 1
            db.commit()
            print(f"Marked {marked} as handled.")
            return 0
        rows = _rows(db, args.status, args.days)
        if args.json:
            print(json.dumps(
                [
                    {
                        "id": r.id,
                        "created_at": r.created_at.isoformat(),
                        "status": r.status,
                        "account": r.user_id,
                        "page": r.page,
                        "lang": r.lang,
                        "message": r.message,
                    }
                    for r in rows
                ],
                ensure_ascii=False,
                indent=1,
            ))
        else:
            print(feedback_service.as_text(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
