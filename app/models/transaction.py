import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import Currency, TransactionType, enum_values
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class Transaction(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    category_name_snapshot: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency", values_callable=enum_values), nullable=False
    )
    rate_used: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, name="transaction_type", values_callable=enum_values), nullable=False
    )
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        Index("ix_transactions_user_created", "user_id", "created_at", "id"),
        Index("ix_transactions_account_created", "account_id", "created_at", "id"),
    )
