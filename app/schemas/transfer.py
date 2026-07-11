from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import Currency


class TransferCreate(BaseModel):
    source_account_id: UUID
    destination_account_id: UUID
    source_amount: Decimal = Field(gt=0)
    rate_override: Decimal | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, max_length=500)


class TransferUpdate(BaseModel):
    source_account_id: UUID | None = None
    destination_account_id: UUID | None = None
    source_amount: Decimal | None = Field(default=None, gt=0)
    rate_override: Decimal | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, max_length=500)


class TransferRead(BaseModel):
    id: UUID
    source_account_id: UUID
    destination_account_id: UUID
    source_amount: Decimal
    source_currency: Currency
    destination_amount: Decimal
    destination_currency: Currency
    rate_used: Decimal | None
    description: str | None
    created_at: datetime
