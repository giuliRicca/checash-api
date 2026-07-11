import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import Currency, enum_values
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class Transfer(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "transfers"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    source_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    destination_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    source_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    source_currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency", values_callable=enum_values), nullable=False
    )
    destination_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    destination_currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency", values_callable=enum_values), nullable=False
    )
    rate_used: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        CheckConstraint("source_amount > 0", name="ck_transfers_source_amount_positive"),
        CheckConstraint("destination_amount > 0", name="ck_transfers_destination_amount_positive"),
        CheckConstraint(
            "source_account_id <> destination_account_id", name="ck_transfers_distinct_accounts"
        ),
        Index("ix_transfers_user_created", "user_id", "created_at", "id"),
        Index("ix_transfers_source_created", "source_account_id", "created_at", "id"),
        Index("ix_transfers_destination_created", "destination_account_id", "created_at", "id"),
    )
