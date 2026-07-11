"""initial schema

Revision ID: 202607030001
Revises:
Create Date: 2026-07-03 00:01:00.000000

"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202607030001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

currency_enum = postgresql.ENUM("ARS", "USD", name="currency", create_type=False)
rate_type_enum = postgresql.ENUM("blue", "mep", "tarjeta", name="rate_type", create_type=False)
transaction_type_enum = postgresql.ENUM(
    "expense", "income", name="transaction_type", create_type=False
)
rate_provider_enum = postgresql.ENUM("dolarapi", name="rate_provider", create_type=False)

SYSTEM_CATEGORIES = [
    ("groceries", "Groceries"),
    ("transport", "Transport"),
    ("utilities", "Utilities"),
    ("rent", "Rent"),
    ("health", "Health"),
    ("entertainment", "Entertainment"),
    ("salary", "Salary"),
    ("miscellaneous", "Miscellaneous"),
]


def upgrade() -> None:
    bind = op.get_bind()
    currency_enum.create(bind, checkfirst=True)
    rate_type_enum.create(bind, checkfirst=True)
    transaction_type_enum.create(bind, checkfirst=True)
    rate_provider_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("default_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("default_category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_categories_system_slug_unique",
        "categories",
        ["slug"],
        unique=True,
        postgresql_where=sa.text("user_id IS NULL"),
    )
    op.create_index(
        "ix_categories_user_slug_unique",
        "categories",
        ["user_id", "slug"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )

    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("currency", currency_enum, nullable=False),
        sa.Column("opening_balance", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("balance", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("rate_type", rate_type_enum, nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"])

    op.create_foreign_key(
        "fk_users_default_account_id_accounts",
        "users",
        "accounts",
        ["default_account_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_users_default_category_id_categories",
        "users",
        "categories",
        ["default_category_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_name_snapshot", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", currency_enum, nullable=False),
        sa.Column("rate_used", sa.Numeric(18, 6), nullable=True),
        sa.Column("type", transaction_type_enum, nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
    )
    op.create_index("ix_transactions_user_created", "transactions", ["user_id", "created_at", "id"])
    op.create_index(
        "ix_transactions_account_created", "transactions", ["account_id", "created_at", "id"]
    )

    op.create_table(
        "transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destination_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("source_currency", currency_enum, nullable=False),
        sa.Column("destination_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("destination_currency", currency_enum, nullable=False),
        sa.Column("rate_used", sa.Numeric(18, 6), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["destination_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("source_amount > 0", name="ck_transfers_source_amount_positive"),
        sa.CheckConstraint(
            "destination_amount > 0", name="ck_transfers_destination_amount_positive"
        ),
        sa.CheckConstraint(
            "source_account_id <> destination_account_id",
            name="ck_transfers_distinct_accounts",
        ),
    )
    op.create_index("ix_transfers_user_created", "transfers", ["user_id", "created_at", "id"])
    op.create_index(
        "ix_transfers_source_created", "transfers", ["source_account_id", "created_at", "id"]
    )
    op.create_index(
        "ix_transfers_destination_created",
        "transfers",
        ["destination_account_id", "created_at", "id"],
    )

    op.create_table(
        "exchange_rates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", rate_provider_enum, nullable=False),
        sa.Column("rate_type", rate_type_enum, nullable=False),
        sa.Column("value", sa.Numeric(18, 6), nullable=False),
        sa.Column(
            "fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.CheckConstraint("value > 0", name="ck_exchange_rates_value_positive"),
    )
    op.create_index(
        "ix_exchange_rates_lookup",
        "exchange_rates",
        ["provider", "rate_type", sa.text("fetched_at DESC")],
    )
    op.create_index(
        "uq_exchange_rates_provider_type_effective_date",
        "exchange_rates",
        ["provider", "rate_type", "effective_date"],
        unique=True,
    )

    categories_table = sa.table(
        "categories",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("is_system", sa.Boolean),
    )
    op.bulk_insert(
        categories_table,
        [
            {
                "id": uuid4(),
                "slug": slug,
                "name": name,
                "is_system": True,
            }
            for slug, name in SYSTEM_CATEGORIES
        ],
        multiinsert=False,
    )


def downgrade() -> None:
    op.drop_table("exchange_rates")
    op.drop_index("ix_transfers_destination_created", table_name="transfers")
    op.drop_index("ix_transfers_source_created", table_name="transfers")
    op.drop_index("ix_transfers_user_created", table_name="transfers")
    op.drop_table("transfers")
    op.drop_index("ix_transactions_account_created", table_name="transactions")
    op.drop_index("ix_transactions_user_created", table_name="transactions")
    op.drop_table("transactions")
    op.drop_constraint("fk_users_default_category_id_categories", "users", type_="foreignkey")
    op.drop_constraint("fk_users_default_account_id_accounts", "users", type_="foreignkey")
    op.drop_index("ix_accounts_user_id", table_name="accounts")
    op.drop_table("accounts")
    op.drop_index("ix_categories_user_slug_unique", table_name="categories")
    op.drop_index("ix_categories_system_slug_unique", table_name="categories")
    op.drop_table("categories")
    op.drop_table("users")

    bind = op.get_bind()
    rate_provider_enum.drop(bind, checkfirst=True)
    transaction_type_enum.drop(bind, checkfirst=True)
    rate_type_enum.drop(bind, checkfirst=True)
    currency_enum.drop(bind, checkfirst=True)
