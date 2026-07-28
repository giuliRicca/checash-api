import base64
import binascii
import json
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
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
        kind = payload["kind"]
        if kind not in {KIND_TRANSACTION, KIND_TRANSFER}:
            raise ValueError("Unsupported activity kind")
        return datetime.fromisoformat(payload["created_at"]), kind, UUID(payload["id"])
    except (
        KeyError,
        TypeError,
        ValueError,
        UnicodeDecodeError,
        binascii.Error,
        json.JSONDecodeError,
    ) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid cursor") from exc


def cursor_sort_key(item: ActivityItem) -> tuple[datetime, str, str]:
    return item.created_at, item.kind, str(item.id)


def apply_cursor(
    statement,
    model: type[Transaction] | type[Transfer],
    kind: str,
    cursor: tuple[datetime, str, UUID] | None,
):
    if cursor is None:
        return statement

    created_at, cursor_kind, item_id = cursor
    if kind < cursor_kind:
        return statement.where(model.created_at <= created_at)
    if kind == cursor_kind:
        return statement.where(
            or_(
                model.created_at < created_at,
                and_(model.created_at == created_at, model.id < item_id),
            )
        )
    return statement.where(model.created_at < created_at)


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

    query_limit = limit + 1
    transaction_stmt = (
        select(Transaction, Account)
        .join(Account, Account.id == Transaction.account_id)
        .where(Transaction.user_id == user_id)
    )
    transfer_stmt = select(Transfer).where(Transfer.user_id == user_id)
    if account_id is not None:
        transaction_stmt = transaction_stmt.where(Transaction.account_id == account_id)
        transfer_stmt = transfer_stmt.where(
            or_(
                Transfer.source_account_id == account_id,
                Transfer.destination_account_id == account_id,
            )
        )

    transaction_stmt = apply_cursor(transaction_stmt, Transaction, KIND_TRANSACTION, decoded_cursor)
    transfer_stmt = apply_cursor(transfer_stmt, Transfer, KIND_TRANSFER, decoded_cursor)

    transactions = list(
        await session.execute(
            transaction_stmt.order_by(Transaction.created_at.desc(), Transaction.id.desc()).limit(
                query_limit
            )
        )
    )
    transfers = list(
        await session.scalars(
            transfer_stmt.order_by(Transfer.created_at.desc(), Transfer.id.desc()).limit(
                query_limit
            )
        )
    )

    items = [
        transaction_to_activity(transaction, account.currency)
        for transaction, account in transactions
    ]
    items.extend(transfer_to_activity(item) for item in transfers)
    items.sort(key=cursor_sort_key, reverse=True)
    page = items[:limit]
    next_cursor = encode_cursor(page[-1]) if len(items) > limit and page else None
    return ActivityFeed(items=page, next_cursor=next_cursor)


def transaction_to_activity(transaction: Transaction, account_currency) -> ActivityItem:
    return ActivityItem(
        kind=KIND_TRANSACTION,
        id=transaction.id,
        created_at=transaction.created_at,
        occurred_at=transaction.occurred_at,
        account_id=transaction.account_id,
        amount=transaction.amount,
        account_amount=transaction.account_amount,
        currency=transaction.currency,
        account_currency=account_currency,
        rate_used=transaction.rate_used,
        is_adjustment=transaction.is_adjustment,
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
