from datetime import datetime

from sqlalchemy import (
    Boolean,
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


class EvaluationRun(Base):
    """One execution of the evaluation suite.

    A run compares several RAG configurations (for example a naive
    baseline against the improved pipeline) over the same dataset.
    """

    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    dataset: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="running",
        index=True,
    )

    case_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    pipelines: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    summary: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class EvaluationCase(Base):
    """Per-question result inside an evaluation run."""

    __tablename__ = "evaluation_cases"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    run_id: Mapped[int] = mapped_column(
        ForeignKey(
            "evaluation_runs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    pipeline: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    expected_answer: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    expected_document_ids: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    answer: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    retrieved_document_ids: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    metrics: Mapped[dict | None] = mapped_column(
        JSONB,
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

    passed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
