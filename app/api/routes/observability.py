from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.dependencies import get_db
from app.repositories.observability import (
    ObservabilityRepository,
)
from app.services.observability import (
    build_overview,
)

router = APIRouter(
    prefix="/observability",
    tags=["Observability"],
)


@router.get("/overview")
async def observability_overview(
    hours: int = 24,
    session: AsyncSession = Depends(get_db),
):
    return await build_overview(
        session,
        hours=max(1, min(hours, 168)),
    )


@router.get("/requests")
async def recent_requests(
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
):
    repository = ObservabilityRepository(
        session
    )

    records = await repository.recent(
        limit=max(1, min(limit, 200))
    )

    return [
        {
            "id": record.id,
            "endpoint": record.endpoint,
            "pipeline": record.pipeline,
            "question": record.question,
            "route": record.route,
            "model": record.model,
            "latency_ms": record.latency_ms,
            "prompt_tokens": (
                record.prompt_tokens
            ),
            "completion_tokens": (
                record.completion_tokens
            ),
            "total_tokens": (
                record.total_tokens
            ),
            "success": record.success,
            "error": record.error,
            "created_at": (
                record.created_at.isoformat()
            ),
        }
        for record in records
    ]
