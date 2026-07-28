"""seed system categories

Revision ID: 202607240001
Revises: 202607230001
Create Date: 2026-07-24 00:01:00.000000

"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202607240001"
down_revision: str | None = "202607230001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

transaction_type_enum = postgresql.ENUM(
    "expense", "income", name="transaction_type", create_type=False
)

SYSTEM_CATEGORIES = [
    ("groceries", "Groceries", "expense"),
    ("personal", "Personal", "expense"),
    ("utilities", "Utilities", "expense"),
    ("rent", "Rent", "expense"),
    ("health", "Health", "expense"),
    ("eating out", "Eating Out", "expense"),
    ("entertainment", "Entertainment", "expense"),
    ("salary", "Salary", "income"),
    ("miscellaneous", "Miscellaneous", "expense"),
]


def upgrade() -> None:
    categories_table = sa.table(
        "categories",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("type", transaction_type_enum),
        sa.column("is_system", sa.Boolean),
    )
    bind = op.get_bind()

    for slug, name, category_type in SYSTEM_CATEGORIES:
        exists = bind.execute(
            sa.text("SELECT 1 FROM categories WHERE user_id IS NULL AND slug = :slug"),
            {"slug": slug},
        ).scalar()
        if exists is None:
            op.bulk_insert(
                categories_table,
                [
                    {
                        "id": uuid4(),
                        "slug": slug,
                        "name": name,
                        "type": category_type,
                        "is_system": True,
                    }
                ],
                multiinsert=False,
            )


def downgrade() -> None:
    # System categories may already be referenced by user transactions.
    # Keep historical rows intact when rolling back only this seed migration.
    return None
