from fastapi import APIRouter, Depends
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.waterbody import State, Waterbody
from app.schemas.waterbody import StateOut

router = APIRouter(prefix="/states", tags=["states"])


@router.get("", response_model=list[StateOut])
def list_states(db: Session = Depends(get_db)) -> list[StateOut]:
    """Which states have data coverage, so the frontend never hardcodes it
    and adding a state is a data change, not a code change.

    `has_waterbodies` uses EXISTS rather than a count: the map only needs to
    know lit-or-grey, and EXISTS stops at the first lake it finds instead of
    counting every one (a count over a national table is a full scan on
    every page load).
    """
    has_any = exists().where(Waterbody.state_id == State.id)
    rows = db.execute(select(State, has_any.label("has_waterbodies")).order_by(State.code)).all()
    return [
        StateOut(
            id=state.id,
            name=state.name,
            code=state.code,
            official_source_url=state.official_source_url,
            has_waterbodies=bool(has),
        )
        for state, has in rows
    ]
