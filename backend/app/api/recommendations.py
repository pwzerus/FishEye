from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.services.recommendations import WaterbodyNotFound, build_recommendations

router = APIRouter(tags=["recommendations"])


@router.post("/recommendations", response_model=RecommendationResponse)
def post_recommendations(
    payload: RecommendationRequest,
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    """Ranked spot candidates for a waterbody, with each factor's
    contribution and reason exposed (PRD §5.2 / §9).

    A candidate's `score` is only meaningful alongside its `confidence`:
    habitat data doesn't exist yet, so every candidate scores on at most
    75% of the intended signal, and the response says so per-candidate
    rather than hiding it behind a single number.
    """
    try:
        result = build_recommendations(
            db,
            waterbody_id=payload.waterbody_id,
            target_species=payload.target_species,
            limit=payload.limit,
        )
    except WaterbodyNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return RecommendationResponse(**result)
