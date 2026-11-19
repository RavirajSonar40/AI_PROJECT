from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InteractionEvent(Base):
    """A single signal about what a user found useful.

    Recommendations and personalisation are derived from these events:
    searches, questions, document opens and explicit thumbs up/down.
    """

    __tablename__ = "interaction_events"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    document_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "documents.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    chunk_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "document_chunks.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    query: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    relevance: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    event_metadata: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
