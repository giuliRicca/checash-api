"""add balance adjustments

Revision ID: 202607220002
Revises: 202607220001
Create Date: 2026-07-22 00:02:00.000000

"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202607220002"
down_revision: str | None = "202607220001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

transaction_type_enum = postgresql.ENUM(
    "expense", "income", name="transaction_type", create_type=False
)


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("is_adjustment", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    categories_table = sa.table(
        "categories",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("type", transaction_type_enum),
        sa.column("is_system", sa.Boolean),
    )
    op.bulk_insert(
        categories_table,
        [
            {
                "id": uuid4(),
                "name": "Balance adjustment",
                "slug": "balance-adjustment-expense",
                "type": "expense",
                "is_system": True,
            },
            {
                "id": uuid4(),
                "name": "Balance adjustment",
                "slug": "balance-adjustment-income",
                "type": "income",
                "is_system": True,
            },
        ],
        multiinsert=False,
    )


def downgrade() -> None:
    op.execute(
        """
        WITH deleted_transactions AS (
            SELECT transaction.account_id,
                   SUM(
                       CASE WHEN transaction.type = 'expense'::transaction_type
                            THEN transaction.amount
                            ELSE -transaction.amount
                       END
                   ) AS balance_delta
            FROM transactions AS transaction
            JOIN categories AS category ON category.id = transaction.category_id
            WHERE category.user_id IS NULL
              AND category.slug IN ('balance-adjustment-expense', 'balance-adjustment-income')
            GROUP BY transaction.account_id
        )
        UPDATE accounts AS account
        SET balance = account.balance + deleted_transactions.balance_delta
        FROM deleted_transactions
        WHERE account.id = deleted_transactions.account_id
        """
    )
    op.execute(
        """
        DELETE FROM transactions
        WHERE category_id IN (
            SELECT id
            FROM categories
            WHERE user_id IS NULL
              AND slug IN ('balance-adjustment-expense', 'balance-adjustment-income')
        )
        """
    )
    op.execute(
        """
        DELETE FROM categories
        WHERE user_id IS NULL
          AND slug IN ('balance-adjustment-expense', 'balance-adjustment-income')
        """
    )
    op.drop_column("transactions", "is_adjustment")
