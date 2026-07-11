from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, Index, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import RateProvider, RateType, enum_values
from app.models.mixins import UUIDPrimaryKeyMixin


class ExchangeRate(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "exchange_rates"

    provider: Mapped[RateProvider] = mapped_column(
        Enum(RateProvider, name="rate_provider", values_callable=enum_values), nullable=False
    )
    rate_type: Mapped[RateType] = mapped_column(
        Enum(RateType, name="rate_type", values_callable=enum_values), nullable=False
    )
    value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        CheckConstraint("value > 0", name="ck_exchange_rates_value_positive"),
        Index("ix_exchange_rates_lookup", "provider", "rate_type", fetched_at.desc()),
        Index(
            "uq_exchange_rates_provider_type_effective_date",
            "provider",
            "rate_type",
            "effective_date",
            unique=True,
        ),
    )
