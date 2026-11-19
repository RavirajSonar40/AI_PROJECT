from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LLMRequestLog(Base):
    """Telemetry for a single user-facing AI request.

    Token counts are estimates unless the provider exposes usage metadata.
    The dashboard labels them accordingly.
    """

    __tablename__ = "llm_request_logs"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    endpoint: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
    )

    pipeline: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="rag",
    )

    question: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    route: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    model: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    latency_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    prompt_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    completion_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    usage_source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="estimated",
    )

    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
