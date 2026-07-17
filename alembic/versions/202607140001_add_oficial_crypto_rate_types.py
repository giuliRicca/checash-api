"""add oficial and crypto rate types

Revision ID: 202607140001
Revises: 202607030001
Create Date: 2026-07-14 00:01:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "202607140001"
down_revision: str | None = "202607030001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE rate_type ADD VALUE IF NOT EXISTS 'oficial'")
    op.execute("ALTER TYPE rate_type ADD VALUE IF NOT EXISTS 'crypto'")


def downgrade() -> None:
    # This project has no production data yet. Downgrade normalizes unsupported
    # account values and removes rate-cache rows before recreating PostgreSQL enum.
    op.execute("UPDATE accounts SET rate_type = 'blue' WHERE rate_type IN ('oficial', 'crypto')")
    op.execute("DELETE FROM exchange_rates WHERE rate_type IN ('oficial', 'crypto')")
    op.execute("ALTER TABLE accounts ALTER COLUMN rate_type TYPE varchar USING rate_type::text")
    op.execute(
        "ALTER TABLE exchange_rates ALTER COLUMN rate_type TYPE varchar USING rate_type::text"
    )
    op.execute("DROP TYPE rate_type")
    op.execute("CREATE TYPE rate_type AS ENUM ('blue', 'mep', 'tarjeta')")
    op.execute(
        "ALTER TABLE accounts ALTER COLUMN rate_type TYPE rate_type USING rate_type::rate_type"
    )
    op.execute(
        "ALTER TABLE exchange_rates ALTER COLUMN rate_type TYPE rate_type "
        "USING rate_type::rate_type"
    )
