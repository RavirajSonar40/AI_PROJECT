from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.schemas.recommendation import (
    RecommendationEventRequest,
    RecommendationFeedbackRequest,
    RecommendationRequest,
    RecommendationResponse,
)
from app.services.recommendation_service import (
    RecommendationService,
)

router = APIRouter(
    prefix="/recommendations",
    tags=["Recommendations"],
)


@router.post(
    "",
    response_model=RecommendationResponse,
)
async def recommend_documents(
    payload: RecommendationRequest,
    session: AsyncSession = Depends(get_db),
):
    service = RecommendationService(session)

    return await service.recommend(
        user_id=payload.user_id,
        limit=payload.limit,
        include_seen=payload.include_seen,
    )


@router.post("/feedback")
async def submit_feedback(
    payload: RecommendationFeedbackRequest,
    session: AsyncSession = Depends(get_db),
):
    service = RecommendationService(session)

    return await service.record_feedback(
        user_id=payload.user_id,
        document_id=payload.document_id,
        relevant=payload.relevant,
        note=payload.note,
    )


@router.post("/events")
async def record_event(
    payload: RecommendationEventRequest,
    session: AsyncSession = Depends(get_db),
):
    service = RecommendationService(session)

    return await service.record_event(
        user_id=payload.user_id,
        event_type=payload.event_type,
        document_id=payload.document_id,
        query=payload.query,
    )


@router.get("/{user_id}/history")
async def recommendation_history(
    user_id: str,
    limit: int = 20,
    session: AsyncSession = Depends(get_db),
):
    service = RecommendationService(session)

    return await service.history(
        user_id=user_id,
        limit=max(1, min(limit, 100)),
    )
