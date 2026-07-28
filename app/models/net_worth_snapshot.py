import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class NetWorthSnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "net_worth_snapshots"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    total_ars: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_usd: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_net_worth_snapshots_user_captured_at", "user_id", "captured_at"),)
