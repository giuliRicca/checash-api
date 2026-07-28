"""add transaction occurred at

Revision ID: 202607200001
Revises: 202607140002
Create Date: 2026-07-20 00:01:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202607200001"
down_revision: str | None = "202607140002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "transactions", sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.execute("UPDATE transactions SET occurred_at = created_at")
    op.alter_column("transactions", "occurred_at", nullable=False)
    op.create_index(
        "ix_transactions_user_occurred", "transactions", ["user_id", "occurred_at", "id"]
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_user_occurred", table_name="transactions")
    op.drop_column("transactions", "occurred_at")
