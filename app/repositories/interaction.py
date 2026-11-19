from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interaction import InteractionEvent


class InteractionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self,
        user_id: str,
        event_type: str,
        document_id: int | None = None,
        chunk_id: int | None = None,
        query: str | None = None,
        relevance: int | None = None,
        metadata: dict | None = None,
    ) -> InteractionEvent:
        event = InteractionEvent(
            user_id=user_id,
            event_type=event_type,
            document_id=document_id,
            chunk_id=chunk_id,
            query=query,
            relevance=relevance,
            event_metadata=metadata,
        )

        self.session.add(event)

        await self.session.commit()
        await self.session.refresh(event)

        return event

    async def recent_for_user(
        self,
        user_id: str,
        limit: int = 100,
    ) -> list[InteractionEvent]:
        result = await self.session.execute(
            select(InteractionEvent)
            .where(
                InteractionEvent.user_id == user_id
            )
            .order_by(
                InteractionEvent.created_at.desc()
            )
            .limit(limit)
        )

        return list(result.scalars().all())

    async def history_for_user(
        self,
        user_id: str,
        limit: int = 20,
    ) -> list[InteractionEvent]:
        return await self.recent_for_user(
            user_id,
            limit=limit,
        )

    async def popularity(
        self,
        days: int = 90,
    ) -> dict[int, int]:
        """Count interactions per document across all users."""

        since = datetime.now(timezone.utc) - timedelta(
            days=days
        )

        result = await self.session.execute(
            select(
                InteractionEvent.document_id,
                func.count(
                    InteractionEvent.id
                ).label("total"),
            )
            .where(
                InteractionEvent.document_id.is_not(
                    None
                ),
                InteractionEvent.created_at >= since,
            )
            .group_by(
                InteractionEvent.document_id
            )
        )

        return {
            document_id: int(total)
            for document_id, total in result.all()
            if document_id is not None
        }

    async def count_for_user(
        self,
        user_id: str,
    ) -> int:
        result = await self.session.execute(
            select(func.count(InteractionEvent.id))
            .where(
                InteractionEvent.user_id == user_id
            )
        )

        return int(result.scalar_one())
