import base64
import json
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.schemas.activity import ActivityFeed, ActivityItem
from app.services.accounts import get_owned_account

KIND_TRANSACTION = "transaction"
KIND_TRANSFER = "transfer"


def encode_cursor(item: ActivityItem) -> str:
    payload = {
        "created_at": item.created_at.isoformat(),
        "kind": item.kind,
        "id": str(item.id),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_cursor(cursor: str | None) -> tuple[datetime, str, UUID] | None:
    if cursor is None:
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return datetime.fromisoformat(payload["created_at"]), payload["kind"], UUID(payload["id"])
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid cursor") from exc


def cursor_sort_key(item: ActivityItem) -> tuple[datetime, str, str]:
    return item.created_at, item.kind, str(item.id)


def is_before_cursor(item: ActivityItem, cursor: tuple[datetime, str, UUID] | None) -> bool:
    if cursor is None:
        return True
    created_at, kind, item_id = cursor
    return cursor_sort_key(item) < (created_at, kind, str(item_id))


async def get_activity_feed(
    session: AsyncSession,
    user_id: UUID,
    limit: int,
    cursor: str | None,
    account_id: UUID | None = None,
) -> ActivityFeed:
    decoded_cursor = decode_cursor(cursor)
    if account_id is not None:
        await get_owned_account(session, user_id, account_id)

    query_limit = limit * 2 + 2
    transaction_stmt = select(Transaction).where(Transaction.user_id == user_id)
    transfer_stmt = select(Transfer).where(Transfer.user_id == user_id)
    if account_id is not None:
        transaction_stmt = transaction_stmt.where(Transaction.account_id == account_id)
        transfer_stmt = transfer_stmt.where(
            or_(
                Transfer.source_account_id == account_id,
                Transfer.destination_account_id == account_id,
            )
        )

    transactions = list(
        await session.scalars(
            transaction_stmt.order_by(Transaction.created_at.desc()).limit(query_limit)
        )
    )
    transfers = list(
        await session.scalars(transfer_stmt.order_by(Transfer.created_at.desc()).limit(query_limit))
    )

    items = [transaction_to_activity(item) for item in transactions]
    items.extend(transfer_to_activity(item) for item in transfers)
    filtered = [item for item in items if is_before_cursor(item, decoded_cursor)]
    filtered.sort(key=cursor_sort_key, reverse=True)
    page = filtered[:limit]
    next_cursor = encode_cursor(page[-1]) if len(filtered) > limit and page else None
    return ActivityFeed(items=page, next_cursor=next_cursor)


def transaction_to_activity(transaction: Transaction) -> ActivityItem:
    return ActivityItem(
        kind=KIND_TRANSACTION,
        id=transaction.id,
        created_at=transaction.created_at,
        account_id=transaction.account_id,
        amount=transaction.amount,
        currency=transaction.currency,
        rate_used=transaction.rate_used,
        transaction_type=transaction.type,
        category_id=transaction.category_id,
        category_name=transaction.category_name_snapshot,
        description=transaction.description,
    )


def transfer_to_activity(transfer: Transfer) -> ActivityItem:
    return ActivityItem(
        kind=KIND_TRANSFER,
        id=transfer.id,
        created_at=transfer.created_at,
        source_account_id=transfer.source_account_id,
        destination_account_id=transfer.destination_account_id,
        source_amount=transfer.source_amount,
        source_currency=transfer.source_currency,
        destination_amount=transfer.destination_amount,
        destination_currency=transfer.destination_currency,
        rate_used=transfer.rate_used,
        description=transfer.description,
    )
