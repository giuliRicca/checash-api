"""add net worth snapshots

Revision ID: 202607220001
Revises: 202607200002
Create Date: 2026-07-22 00:01:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202607220001"
down_revision: str | None = "202607200002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "net_worth_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_ars", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_usd", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_net_worth_snapshots_user_captured_at",
        "net_worth_snapshots",
        ["user_id", "captured_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_net_worth_snapshots_user_captured_at", table_name="net_worth_snapshots")
    op.drop_table("net_worth_snapshots")
