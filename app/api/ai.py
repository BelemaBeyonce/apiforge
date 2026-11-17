from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import Field
from sqlalchemy import select

from app.api.routes import DB, Actor, PositiveId
from app.models import AIEvaluation
from app.schemas import StrictModel
from app.services.ai import AIFeedback, AIProvider, get_provider, request_ai, review_ai
from app.services.tasks import require_evaluation

router = APIRouter(tags=["AI evaluation"])


class AIRequest(StrictModel):
    consent_to_external: bool = False


class AIRead(StrictModel):
    model_config = {"from_attributes": True}
    id: int
    evaluation_id: int
    requested_by: int
    provider: str
    model_name: str
    prompt_version: str
    status: str
    feedback: AIFeedback | None
    safe_metadata: dict
    error_code: str | None
    reviewed_by: int | None
    review_note: str | None
    reviewed_at: datetime | None
    created_at: datetime


class HumanReview(StrictModel):
    decision: Literal["accepted", "rejected"]
    note: Annotated[str, Field(min_length=1, max_length=2000)]


@router.post("/evaluations/{evaluation_id}/ai", response_model=AIRead, status_code=201)
def create_ai(
    evaluation_id: PositiveId,
    data: AIRequest,
    db: DB,
    actor: Actor,
    provider: Annotated[AIProvider, Depends(get_provider)],
):
    return request_ai(db, evaluation_id, actor, data.consent_to_external, provider)


@router.get("/evaluations/{evaluation_id}/ai")
def list_ai(
    evaluation_id: PositiveId,
    db: DB,
    actor: Actor,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    original = require_evaluation(db, evaluation_id, actor)
    items = db.scalars(
        select(AIEvaluation)
        .where(AIEvaluation.evaluation_id == evaluation_id)
        .order_by(AIEvaluation.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return {
        "deterministic_score": original.score,
        "engine_version": original.engine_version,
        "items": [
            {
                "result": AIRead.model_validate(item).model_dump(),
                "advisory_score_delta": round(item.feedback["score"] - original.score, 2)
                if item.feedback
                else None,
            }
            for item in items
        ],
        "limit": limit,
        "offset": offset,
        "warning": "AI scores are advisory and never replace deterministic results",
    }


@router.post("/ai-evaluations/{ai_id}/review", response_model=AIRead)
def human_review(ai_id: PositiveId, data: HumanReview, db: DB, actor: Actor):
    return review_ai(db, ai_id, actor, data.decision, data.note)
