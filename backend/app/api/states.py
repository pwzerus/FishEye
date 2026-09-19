from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.waterbody import State
from app.schemas.waterbody import StateOut

router = APIRouter(prefix="/states", tags=["states"])


@router.get("", response_model=list[StateOut])
def list_states(db: Session = Depends(get_db)) -> list[State]:
    """Which states have data coverage. MVP has exactly one (TX) — this
    endpoint exists so the frontend never has to hardcode that, and so
    adding a second state later is a data change, not a code change."""
    return list(db.scalars(select(State)).all())
