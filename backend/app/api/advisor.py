from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.advisor import AdvisorRequest, AdvisorResponse, AdvisorTraceOut
from app.services import ai_advisor
from app.services.recommendations import WaterbodyNotFound

router = APIRouter(prefix="/advisor", tags=["advisor"])


@router.post("/explain", response_model=AdvisorResponse)
def explain_recommendations(
    payload: AdvisorRequest, db: Session = Depends(get_db)
) -> AdvisorResponse:
    """PRD §5.1: explain the rule engine's ranking in plain language.

    Note there is no error path for "the model failed" — that's deliberate.
    A model outage or a rejected (ungrounded) answer degrades to the fixed
    template and still returns 200, because the recommendation itself is
    perfectly valid without any prose attached to it. `answer_source` and
    `trace.outcome` tell an honest caller exactly what happened.
    """
    try:
        result = ai_advisor.explain(
            db,
            waterbody_id=payload.waterbody_id,
            target_species=payload.target_species,
            limit=payload.limit,
        )
    except WaterbodyNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    server_fields = ai_advisor.server_controlled_fields(result.facts)
    trace = result.trace

    return AdvisorResponse(
        waterbody_id=result.facts["waterbody_id"],
        waterbody_name=result.facts["waterbody_name"],
        target_species=result.facts["target_species"],
        explanation=result.explanation,
        answer_source=result.answer_source,
        trace=AdvisorTraceOut(
            trace_id=trace.trace_id,
            provider=trace.provider,
            model=trace.model,
            latency_ms=round(trace.latency_ms, 2),
            prompt_tokens=trace.prompt_tokens,
            completion_tokens=trace.completion_tokens,
            estimated_cost_usd=round(trace.estimated_cost_usd, 6),
            validation_attempts=trace.validation_attempts,
            outcome=trace.outcome,
            retrieved_source_count=trace.retrieved_source_count,
            cache_hit=trace.cache_hit,
        ),
        **server_fields,
    )
