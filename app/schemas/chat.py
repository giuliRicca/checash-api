from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import Currency, TransactionType


class ParseMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class ExchangeDetailsDraft(BaseModel):
    destination_currency: Currency | None = None
    rate_override: Decimal | None = Field(default=None, gt=0)
    destination_account_keyword: str | None = None
    destination_account_id: UUID | None = None


class ChatDraft(BaseModel):
    amount: Decimal
    currency: Currency
    account_keyword: str | None
    account_id: UUID | None
    category_id: UUID | None
    category_name: str | None
    transaction_type: TransactionType | str
    description: str | None
    is_exchange: bool
    exchange_details: ExchangeDetailsDraft | None
    needs_review: bool
    occurred_at: datetime | None = None


class ChatConfirmRequest(BaseModel):
    draft: ChatDraft
