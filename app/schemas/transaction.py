from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import Currency, TransactionType


class TransactionCreate(BaseModel):
    account_id: UUID
    category_id: UUID
    amount: Decimal = Field(gt=0)
    type: TransactionType
    description: str | None = Field(default=None, max_length=500)


class TransactionUpdate(BaseModel):
    account_id: UUID | None = None
    category_id: UUID | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    type: TransactionType | None = None
    description: str | None = Field(default=None, max_length=500)


class TransactionRead(BaseModel):
    id: UUID
    account_id: UUID
    category_id: UUID
    category_name_snapshot: str
    amount: Decimal
    currency: Currency
    rate_used: Decimal | None
    type: TransactionType
    description: str | None
    created_at: datetime


class TransactionMonthSummaryRead(BaseModel):
    month_start: datetime
    month_end: datetime
    income_ars: Decimal
    income_usd: Decimal
    expense_ars: Decimal
    expense_usd: Decimal
