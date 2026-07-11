import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import Currency, RateType, enum_values
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class Account(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency", values_callable=enum_values), nullable=False
    )
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    rate_type: Mapped[RateType] = mapped_column(
        Enum(RateType, name="rate_type", values_callable=enum_values), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_accounts_user_id", "user_id"),)
