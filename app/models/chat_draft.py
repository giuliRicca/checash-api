import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class DraftStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"


class ChatDraftSession(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "chat_draft_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[DraftStatus] = mapped_column(
        String(16), default=DraftStatus.PENDING, nullable=False
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_chat_draft_sessions_user_status", "user_id", "status", "expires_at"),
        Index("ix_chat_draft_sessions_expires", "expires_at"),
    )
