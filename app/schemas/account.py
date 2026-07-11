from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import Currency, RateType


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    currency: Currency
    opening_balance: Decimal = Decimal("0.00")
    rate_type: RateType


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    rate_type: RateType | None = None


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
