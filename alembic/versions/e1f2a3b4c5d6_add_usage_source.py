"""record whether token usage came from a provider or an estimate"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "c7f1a2b3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "llm_request_logs",
        sa.Column(
            "usage_source",
            sa.String(length=20),
            nullable=False,
            server_default="estimated",
        ),
    )


def downgrade() -> None:
    op.drop_column("llm_request_logs", "usage_source")
