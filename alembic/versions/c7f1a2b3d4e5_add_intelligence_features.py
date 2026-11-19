"""add recommendations, evaluation and observability tables

Revision ID: c7f1a2b3d4e5
Revises: d4680b504081
Create Date: 2026-11-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c7f1a2b3d4e5"
down_revision: Union[str, Sequence[str], None] = "d4680b504081"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the tables behind personalisation, evaluation and observability."""

    op.create_table(
        "interaction_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=True),
        sa.Column("chunk_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("relevance", sa.Integer(), nullable=True),
        sa.Column(
            "event_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["document_chunks.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_interaction_events_user_id",
        "interaction_events",
        ["user_id"],
    )
    op.create_index(
        "ix_interaction_events_document_id",
        "interaction_events",
        ["document_id"],
    )
    op.create_index(
        "ix_interaction_events_event_type",
        "interaction_events",
        ["event_type"],
    )
    op.create_index(
        "ix_interaction_events_created_at",
        "interaction_events",
        ["created_at"],
    )

    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("case_count", sa.Integer(), nullable=False),
        sa.Column(
            "pipelines",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_evaluation_runs_status",
        "evaluation_runs",
        ["status"],
    )
    op.create_index(
        "ix_evaluation_runs_started_at",
        "evaluation_runs",
        ["started_at"],
    )

    op.create_table(
        "evaluation_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("pipeline", sa.String(length=32), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("expected_answer", sa.Text(), nullable=True),
        sa.Column(
            "expected_document_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column(
            "retrieved_document_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["evaluation_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_evaluation_cases_run_id",
        "evaluation_cases",
        ["run_id"],
    )
    op.create_index(
        "ix_evaluation_cases_pipeline",
        "evaluation_cases",
        ["pipeline"],
    )

    op.create_table(
        "llm_request_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.String(length=120), nullable=False),
        sa.Column("pipeline", sa.String(length=50), nullable=False),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("route", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_llm_request_logs_endpoint",
        "llm_request_logs",
        ["endpoint"],
    )
    op.create_index(
        "ix_llm_request_logs_success",
        "llm_request_logs",
        ["success"],
    )
    op.create_index(
        "ix_llm_request_logs_created_at",
        "llm_request_logs",
        ["created_at"],
    )


def downgrade() -> None:
    """Drop the tables added by this migration."""

    op.drop_index(
        "ix_llm_request_logs_created_at",
        table_name="llm_request_logs",
    )
    op.drop_index(
        "ix_llm_request_logs_success",
        table_name="llm_request_logs",
    )
    op.drop_index(
        "ix_llm_request_logs_endpoint",
        table_name="llm_request_logs",
    )
    op.drop_table("llm_request_logs")

    op.drop_index(
        "ix_evaluation_cases_pipeline",
        table_name="evaluation_cases",
    )
    op.drop_index(
        "ix_evaluation_cases_run_id",
        table_name="evaluation_cases",
    )
    op.drop_table("evaluation_cases")

    op.drop_index(
        "ix_evaluation_runs_started_at",
        table_name="evaluation_runs",
    )
    op.drop_index(
        "ix_evaluation_runs_status",
        table_name="evaluation_runs",
    )
    op.drop_table("evaluation_runs")

    op.drop_index(
        "ix_interaction_events_created_at",
        table_name="interaction_events",
    )
    op.drop_index(
        "ix_interaction_events_event_type",
        table_name="interaction_events",
    )
    op.drop_index(
        "ix_interaction_events_document_id",
        table_name="interaction_events",
    )
    op.drop_index(
        "ix_interaction_events_user_id",
        table_name="interaction_events",
    )
    op.drop_table("interaction_events")
