from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import Currency


class BudgetCreate(BaseModel):
    category_id: UUID
    amount: Decimal = Field(gt=0)
    currency: Currency


class BudgetUpdate(BaseModel):
    category_id: UUID | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    currency: Currency | None = None


class BudgetRead(BaseModel):
    id: UUID
    category_id: UUID
    amount: Decimal
    currency: Currency
    created_at: datetime


class BudgetMonthSummaryRead(BudgetRead):
    category_name: str
    spent: Decimal
    remaining: Decimal
    percentage: Decimal
    status: str
