from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import Currency


class ParseMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class ExchangeDetailsDraft(BaseModel):
    destination_currency: Currency | None = None
    rate_override: Decimal | None = Field(default=None, gt=0)
    destination_account_keyword: str | None = None
    destination_account_id: UUID | None = None


class ChatDraft(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: Currency
    account_keyword: str | None = None
    account_id: UUID | None = None
    category_id: UUID | None = None
    category_name: str | None = Field(default=None, max_length=120)
    transaction_type: Literal["expense", "income", "transfer"]
    description: str | None = Field(default=None, max_length=500)
    is_exchange: bool = False
    exchange_details: ExchangeDetailsDraft | None = None
    needs_review: bool = False
    occurred_at: datetime | None = None


class ChatDraftEnvelope(BaseModel):
    id: UUID
    expires_at: datetime
    draft: ChatDraft


class ChatConfirmRequest(BaseModel):
    draft_id: UUID
    draft: ChatDraft
