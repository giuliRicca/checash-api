"""add category transaction type

Revision ID: 202607140002
Revises: 202607140001
Create Date: 2026-07-14 00:01:00.000000

"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202607140002"
down_revision: str | None = "202607140001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

transaction_type_enum = postgresql.ENUM(
    "expense", "income", name="transaction_type", create_type=False
)


def upgrade() -> None:
    op.add_column("categories", sa.Column("type", transaction_type_enum, nullable=True))

    op.execute(
        """
        UPDATE categories
        SET type = CASE WHEN slug = 'salary' THEN 'income'::transaction_type
                        ELSE 'expense'::transaction_type END
        WHERE user_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE categories AS category
        SET type = CASE
            WHEN EXISTS (
                SELECT 1 FROM transactions
                WHERE category_id = category.id AND type = 'income'
            )
            AND NOT EXISTS (
                SELECT 1 FROM transactions
                WHERE category_id = category.id AND type = 'expense'
            ) THEN 'income'::transaction_type
            ELSE 'expense'::transaction_type
        END
        WHERE category.user_id IS NOT NULL
        """
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
                "name": "Uncategorized income",
                "slug": "uncategorized-income",
                "type": "income",
                "is_system": True,
            }
        ],
        multiinsert=False,
    )
    op.alter_column("categories", "type", nullable=False)


def downgrade() -> None:
    op.execute("DELETE FROM categories WHERE user_id IS NULL AND slug = 'uncategorized-income'")
    op.drop_column("categories", "type")
