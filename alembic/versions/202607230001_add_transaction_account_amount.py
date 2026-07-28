"""add transaction account amount

Revision ID: 202607230001
Revises: 202607220002
Create Date: 2026-07-23 00:01:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202607230001"
down_revision: str | None = "202607220002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("account_amount", sa.Numeric(18, 2), nullable=True))
    op.execute("UPDATE transactions SET account_amount = amount")
    op.alter_column("transactions", "account_amount", nullable=False)
    op.create_check_constraint(
        "ck_transactions_account_amount_positive", "transactions", "account_amount > 0"
    )
    op.create_check_constraint(
        "ck_transactions_rate_used_positive", "transactions", "rate_used IS NULL OR rate_used > 0"
    )


def downgrade() -> None:
    op.drop_constraint("ck_transactions_rate_used_positive", "transactions", type_="check")
    op.drop_constraint("ck_transactions_account_amount_positive", "transactions", type_="check")
    op.drop_column("transactions", "account_amount")
