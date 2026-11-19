"""Personalised knowledge recommendations.

The ranker blends three signals:

* semantic affinity - cosine similarity between a user interest vector
  (a weighted average of the document profiles they engaged with) and each
  document profile (the average of its chunk embeddings);
* behavioural weight - how recently and how often the user engaged with a
  document, with explicit thumbs up/down dominating;
* workspace popularity and freshness as a tie breaker.

With no history at all the service falls back to a transparent cold-start
ranking (popularity + recency) so the panel is never empty.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from math import sqrt

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import (
    RECOMMENDATION_FEEDBACK,
    RECOMMENDATION_REQUESTS,
)
from app.repositories.document import DocumentRepository
from app.repositories.document_chunk import (
    DocumentChunkRepository,
)
from app.repositories.interaction import (
    InteractionRepository,
)

EVENT_WEIGHTS = {
    "open": 1.2,
    "view": 1.0,
    "search": 1.6,
    "ask": 2.2,
}

POSITIVE_FEEDBACK_WEIGHT = 3.5
NEGATIVE_FEEDBACK_WEIGHT = -5.0

SEMANTIC_WEIGHT = 0.50
BEHAVIOUR_WEIGHT = 0.35
POPULARITY_WEIGHT = 0.15

COLD_START_POPULARITY_WEIGHT = 0.60
COLD_START_RECENCY_WEIGHT = 0.40


def _normalize(
    vector: list[float],
) -> list[float]:
    length = sqrt(
        sum(value * value for value in vector)
    )

    if length == 0:
        return vector

    return [
        value / length for value in vector
    ]


def _cosine(
    left: list[float],
    right: list[float],
) -> float:
    if not left or not right:
        return 0.0

    return sum(
        a * b for a, b in zip(left, right)
    )


def _age_days(value: datetime) -> float:
    if value.tzinfo is None:
        value = value.replace(
            tzinfo=timezone.utc
        )

    delta = datetime.now(timezone.utc) - value

    return max(0.0, delta.total_seconds() / 86400)


def _recency_decay(
    value: datetime,
    half_life_days: float = 30.0,
) -> float:
    return 0.5 ** (
        _age_days(value) / half_life_days
    )


class RecommendationService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session
        self.interactions = InteractionRepository(
            session
        )
        self.chunks = DocumentChunkRepository(
            session
        )
        self.documents = DocumentRepository(
            session
        )

    async def recommend(
        self,
        user_id: str,
        limit: int = 5,
        include_seen: bool = False,
    ) -> dict:
        events = (
            await self.interactions
            .recent_for_user(
                user_id,
                limit=100,
            )
        )

        chunks = await self.chunks.list_embedded()
        documents = await self.documents.list_all()

        popularity = (
            await self.interactions.popularity()
        )

        profiles, chunks_by_document = (
            self._build_profiles(chunks)
        )

        by_document, seen = (
            self._build_behaviour(events)
        )

        interest = self._build_interest(
            by_document,
            profiles,
        )

        personalised = any(
            value > 0
            for value in interest
        )

        scored = []

        max_behaviour = max(
            [
                value
                for value in by_document.values()
                if value > 0
            ]
            or [0.0]
        )

        max_popularity = max(
            popularity.values() or [1]
        )

        for document in documents:
            profile = profiles.get(
                document.id
            )

            if profile is None:
                # Nothing indexed yet, so it cannot be recommended.
                continue

            if (
                by_document.get(
                    document.id,
                    0.0,
                )
                <= -3.0
            ):
                # The user explicitly rejected this document.
                continue

            semantic = 0.0

            if personalised:
                semantic = max(
                    0.0,
                    min(
                        1.0,
                        _cosine(
                            interest,
                            profile,
                        ),
                    ),
                )

            behaviour = 0.0

            if max_behaviour > 0:
                behaviour = max(
                    0.0,
                    by_document.get(
                        document.id,
                        0.0,
                    ),
                ) / max_behaviour

            popularity_score = (
                popularity.get(
                    document.id,
                    0,
                )
                / max_popularity
                if max_popularity
                else 0.0
            )

            recency = _recency_decay(
                document.created_at
            )

            if personalised:
                score = (
                    SEMANTIC_WEIGHT * semantic
                    + BEHAVIOUR_WEIGHT
                    * behaviour
                    + POPULARITY_WEIGHT
                    * popularity_score
                )
            else:
                score = (
                    COLD_START_POPULARITY_WEIGHT
                    * popularity_score
                    + COLD_START_RECENCY_WEIGHT
                    * recency
                )

            scored.append(
                {
                    "document_id": document.id,
                    "filename": document.filename,
                    "score": score,
                    "semantic_score": semantic,
                    "behavioural_score": behaviour,
                    "popularity_score": (
                        popularity_score
                    ),
                    "seen": (
                        document.id in seen
                    ),
                    "reason": self._reason(
                        document_id=(
                            document.id
                        ),
                        seen=(
                            document.id
                            in seen
                        ),
                        behaviour=(
                            by_document.get(
                                document.id,
                                0.0,
                            )
                        ),
                        semantic=semantic,
                        popularity=(
                            popularity_score
                        ),
                        personalised=(
                            personalised
                        ),
                    ),
                    "preview": self._preview(
                        chunks_by_document.get(
                            document.id,
                            [],
                        ),
                        interest=(
                            interest
                            if personalised
                            else None
                        ),
                    ),
                    "chunk_count": len(
                        chunks_by_document.get(
                            document.id,
                            [],
                        )
                    ),
                }
            )

        scored.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        if include_seen:
            selected = scored[:limit]
        else:
            # Explicit positive interest always wins, even if the document
            # has already been seen. Otherwise favour exploration.
            positive = [
                item
                for item in scored
                if item["behavioural_score"]
                >= 0.5
            ]

            remaining = [
                item
                for item in scored
                if item["behavioural_score"]
                < 0.5
            ]

            unseen = [
                item
                for item in remaining
                if not item["seen"]
            ]

            seen_items = [
                item
                for item in remaining
                if item["seen"]
            ]

            selected = (
                positive + unseen + seen_items
            )[:limit]

        strategy = (
            "personalised"
            if personalised
            else "cold_start"
        )

        RECOMMENDATION_REQUESTS.labels(
            strategy=strategy
        ).inc()

        return {
            "user_id": user_id,
            "strategy": strategy,
            "interaction_count": len(events),
            "generated_at": (
                datetime.now(timezone.utc)
                .isoformat()
            ),
            "items": [
                {
                    **item,
                    "score": round(
                        item["score"],
                        4,
                    ),
                    "semantic_score": round(
                        item["semantic_score"],
                        4,
                    ),
                    "behavioural_score": round(
                        item[
                            "behavioural_score"
                        ],
                        4,
                    ),
                    "popularity_score": round(
                        item[
                            "popularity_score"
                        ],
                        4,
                    ),
                }
                for item in selected
            ],
        }

    async def record_feedback(
        self,
        user_id: str,
        document_id: int,
        relevant: bool,
        note: str | None = None,
    ) -> dict:
        await self.interactions.record(
            user_id=user_id,
            event_type="feedback",
            document_id=document_id,
            relevance=(
                1 if relevant else -1
            ),
            metadata=(
                {"note": note}
                if note
                else None
            ),
        )

        RECOMMENDATION_FEEDBACK.labels(
            relevant=(
                "true" if relevant else "false"
            )
        ).inc()

        return {
            "user_id": user_id,
            "document_id": document_id,
            "relevant": relevant,
            "status": "recorded",
        }

    async def record_event(
        self,
        user_id: str,
        event_type: str,
        document_id: int | None = None,
        chunk_id: int | None = None,
        query: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        event = await self.interactions.record(
            user_id=user_id,
            event_type=event_type,
            document_id=document_id,
            chunk_id=chunk_id,
            query=query,
            metadata=metadata,
        )

        return {
            "id": event.id,
            "user_id": user_id,
            "event_type": event_type,
            "document_id": document_id,
            "status": "recorded",
        }

    async def history(
        self,
        user_id: str,
        limit: int = 20,
    ) -> dict:
        events = (
            await self.interactions
            .history_for_user(
                user_id,
                limit=limit,
            )
        )

        return {
            "user_id": user_id,
            "count": len(events),
            "events": [
                {
                    "id": event.id,
                    "event_type": (
                        event.event_type
                    ),
                    "document_id": (
                        event.document_id
                    ),
                    "query": event.query,
                    "relevance": (
                        event.relevance
                    ),
                    "created_at": (
                        event.created_at
                        .isoformat()
                    ),
                }
                for event in events
            ],
        }

    @staticmethod
    def _build_profiles(
        chunks,
    ) -> tuple[
        dict[int, list[float]],
        dict[int, list],
    ]:
        grouped: dict[int, list] = defaultdict(
            list
        )

        for chunk in chunks:
            grouped[chunk.document_id].append(
                chunk
            )

        profiles: dict[int, list[float]] = {}
        chunks_by_document: dict[int, list] = (
            {}
        )

        for document_id, items in grouped.items():
            vectors = [
                _normalize(
                    [
                        float(value)
                        for value in item.embedding
                    ]
                )
                for item in items
            ]

            if not vectors:
                continue

            summed = [
                sum(
                    vector[index]
                    for vector in vectors
                )
                / len(vectors)
                for index in range(
                    len(vectors[0])
                )
            ]

            profiles[document_id] = (
                _normalize(summed)
            )

            chunks_by_document[
                document_id
            ] = items

        return profiles, chunks_by_document

    @staticmethod
    def _build_behaviour(
        events,
    ) -> tuple[dict[int, float], set[int]]:
        by_document: dict[int, float] = (
            defaultdict(float)
        )

        seen: set[int] = set()

        for event in events:
            if event.document_id is None:
                continue

            seen.add(event.document_id)

            decay = _recency_decay(
                event.created_at
            )

            if event.event_type == "feedback":
                weight = (
                    POSITIVE_FEEDBACK_WEIGHT
                    if (event.relevance or 0) > 0
                    else NEGATIVE_FEEDBACK_WEIGHT
                )
            else:
                weight = EVENT_WEIGHTS.get(
                    event.event_type,
                    1.0,
                )

            by_document[
                event.document_id
            ] += weight * decay

        return dict(by_document), seen

    @staticmethod
    def _build_interest(
        by_document: dict[int, float],
        profiles: dict[int, list[float]],
    ) -> list[float]:
        if not profiles:
            return []

        dimension = len(
            next(iter(profiles.values()))
        )

        interest = [0.0] * dimension
        total_weight = 0.0

        for document_id, weight in (
            by_document.items()
        ):
            profile = profiles.get(
                document_id
            )

            if (
                profile is None
                or weight <= 0
            ):
                continue

            total_weight += weight

            for index, value in enumerate(
                profile
            ):
                interest[index] += (
                    weight * value
                )

        if total_weight == 0:
            return []

        interest = [
            value / total_weight
            for value in interest
        ]

        return _normalize(interest)

    @staticmethod
    def _preview(
        chunks,
        interest: list[float] | None,
    ) -> str:
        if not chunks:
            return ""

        selected = chunks[0]

        if interest:
            selected = max(
                chunks,
                key=lambda chunk: _cosine(
                    interest,
                    _normalize(
                        [
                            float(value)
                            for value in (
                                chunk.embedding
                            )
                        ]
                    ),
                ),
            )

        text = " ".join(
            selected.content.split()
        )

        if len(text) > 200:
            text = text[:200] + "..."

        return text

    @staticmethod
    def _reason(
        document_id: int,
        seen: bool,
        behaviour: float,
        semantic: float,
        popularity: float,
        personalised: bool,
    ) -> str:
        if behaviour >= POSITIVE_FEEDBACK_WEIGHT:
            return (
                "You marked this as relevant"
            )

        if personalised and semantic >= 0.35:
            return (
                "Semantically close to what "
                "you have been exploring"
            )

        if personalised and behaviour > 0:
            return (
                "Continues your recent "
                "activity"
            )

        if personalised and not seen:
            return (
                "Related but still unexplored "
                "for you"
            )

        if popularity > 0:
            return "Popular across the workspace"

        if not seen:
            return "Recently added to the knowledge base"

        return "Recommended starting point"
