from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.enums import Currency, RateType


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    currency: Currency
    opening_balance: Decimal = Decimal("0.00")
    rate_type: RateType


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    rate_type: RateType | None = None


class AccountAdjustmentCreate(BaseModel):
    target_balance: Decimal
    description: str | None = Field(default=None, max_length=500)
    occurred_at: datetime | None = None

    @field_validator("occurred_at")
    @classmethod
    def validate_occurred_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        if value.tzinfo is None:
            raise ValueError("occurred_at must include a timezone")
        if value > datetime.now(UTC):
            raise ValueError("occurred_at cannot be in the future")
        return value


class AccountRead(BaseModel):
    id: UUID
    name: str
    currency: Currency
    opening_balance: Decimal
    balance: Decimal
    rate_type: RateType
    archived_at: datetime | None


class AccountArchiveResponse(BaseModel):
    account: AccountRead
    warnings: list[str]


class NetWorthRead(BaseModel):
    total_ars: Decimal
    total_usd: Decimal


class NetWorthHistoryPointRead(BaseModel):
    date: date
    total_ars: Decimal
    total_usd: Decimal


class NetWorthHistoryRead(BaseModel):
    month_start: date
    points: list[NetWorthHistoryPointRead]
