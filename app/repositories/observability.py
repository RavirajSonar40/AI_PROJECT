from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.observability import LLMRequestLog


class ObservabilityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self,
        endpoint: str,
        pipeline: str,
        question: str | None,
        route: str | None,
        model: str | None,
        latency_ms: int,
        prompt_tokens: int,
        completion_tokens: int,
        success: bool,
        usage_source: str = "estimated",
        error: str | None = None,
    ) -> LLMRequestLog:
        record = LLMRequestLog(
            endpoint=endpoint,
            pipeline=pipeline,
            question=question,
            route=route,
            model=model,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=(
                prompt_tokens
                + completion_tokens
            ),
            usage_source=usage_source,
            success=success,
            error=error,
        )

        self.session.add(record)

        await self.session.commit()
        await self.session.refresh(record)

        return record

    async def since(
        self,
        hours: int,
    ) -> list[LLMRequestLog]:
        since = datetime.now(timezone.utc) - timedelta(
            hours=hours
        )

        result = await self.session.execute(
            select(LLMRequestLog)
            .where(
                LLMRequestLog.created_at >= since
            )
            .order_by(
                LLMRequestLog.created_at.desc()
            )
        )

        return list(result.scalars().all())

    async def recent(
        self,
        limit: int = 20,
    ) -> list[LLMRequestLog]:
        result = await self.session.execute(
            select(LLMRequestLog)
            .order_by(
                LLMRequestLog.created_at.desc()
            )
            .limit(limit)
        )

        return list(result.scalars().all())

    async def total_count(self) -> int:
        result = await self.session.execute(
            select(func.count(LLMRequestLog.id))
        )

        return int(result.scalar_one())
