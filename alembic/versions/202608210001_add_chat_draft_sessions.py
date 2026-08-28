"""add chat draft sessions

Revision ID: 202608210001
Revises: 202607240002
Create Date: 2026-08-21 00:01:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "202608210001"
down_revision: str | None = "202607240002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_draft_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("source_message", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_chat_draft_sessions_user_status",
        "chat_draft_sessions",
        ["user_id", "status", "expires_at"],
    )
    op.create_index("ix_chat_draft_sessions_expires", "chat_draft_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_chat_draft_sessions_expires", table_name="chat_draft_sessions")
    op.drop_index("ix_chat_draft_sessions_user_status", table_name="chat_draft_sessions")
    op.drop_table("chat_draft_sessions")
