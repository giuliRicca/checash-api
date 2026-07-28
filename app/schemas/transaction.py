from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import Currency, TransactionType


class TransactionCreate(BaseModel):
    account_id: UUID
    category_id: UUID
    amount: Decimal = Field(gt=0)
    currency: Currency | None = None
    type: TransactionType
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


class TransactionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: UUID | None = None
    category_id: UUID | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    currency: Currency | None = None
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


class TransactionRead(BaseModel):
    id: UUID
    account_id: UUID
    category_id: UUID
    category_name_snapshot: str
    amount: Decimal
    account_amount: Decimal
    currency: Currency
    rate_used: Decimal | None
    is_adjustment: bool
    type: TransactionType
    description: str | None
    created_at: datetime
    occurred_at: datetime


class TransactionMonthSummaryRead(BaseModel):
    month_start: datetime
    month_end: datetime
    income_ars: Decimal
    income_usd: Decimal
    expense_ars: Decimal
    expense_usd: Decimal
