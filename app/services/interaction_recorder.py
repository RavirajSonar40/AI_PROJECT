"""Best-effort interaction recording shared by the AI endpoints.

Every question that retrieved documents becomes a personalisation signal.
Failures are rolled back silently so they never affect the user's answer.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.interaction import (
    InteractionRepository,
)


def _document_ids(sources) -> list[int]:
    document_ids: list[int] = []

    for source in sources or []:
        if isinstance(source, int):
            document_id = source
        elif isinstance(source, dict):
            document_id = source.get(
                "document_id"
            )
        else:
            document_id = getattr(
                source,
                "document_id",
                None,
            )

        if document_id is None:
            continue

        document_ids.append(int(document_id))

    # Preserve ranking order, drop duplicates.
    return list(
        dict.fromkeys(document_ids)
    )


async def record_answer_interactions(
    session: AsyncSession,
    user_id: str,
    question: str,
    sources,
    event_type: str = "ask",
    limit: int = 3,
) -> None:
    document_ids = _document_ids(sources)[
        :limit
    ]

    if not document_ids:
        return

    repository = InteractionRepository(session)

    for document_id in document_ids:
        try:
            await repository.record(
                user_id=user_id,
                event_type=event_type,
                document_id=document_id,
                query=question,
            )

        except Exception:
            await session.rollback()
            return
