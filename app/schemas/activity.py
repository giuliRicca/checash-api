from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import Currency, TransactionType


class ActivityItem(BaseModel):
    kind: str
    id: UUID
    created_at: datetime
    account_id: UUID | None = None
    source_account_id: UUID | None = None
    destination_account_id: UUID | None = None
    amount: Decimal | None = None
    currency: Currency | None = None
    source_amount: Decimal | None = None
    source_currency: Currency | None = None
    destination_amount: Decimal | None = None
    destination_currency: Currency | None = None
    rate_used: Decimal | None = None
    transaction_type: TransactionType | None = None
    category_id: UUID | None = None
    category_name: str | None = None
    description: str | None = None


class ActivityFeed(BaseModel):
    items: list[ActivityItem]
    next_cursor: str | None
