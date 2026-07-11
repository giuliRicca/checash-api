from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.schemas.common import quantize_money
from app.services.accounts import ensure_account_active, get_owned_account
from app.services.categories import get_visible_category


def apply_transaction_effect(account: Account, amount, transaction_type: TransactionType) -> None:
    if transaction_type == TransactionType.EXPENSE:
        account.balance = quantize_money(account.balance - amount)
    else:
        account.balance = quantize_money(account.balance + amount)


def reverse_transaction_effect(account: Account, amount, transaction_type: TransactionType) -> None:
    if transaction_type == TransactionType.EXPENSE:
        account.balance = quantize_money(account.balance + amount)
    else:
        account.balance = quantize_money(account.balance - amount)


async def create_transaction(session: AsyncSession, user_id: UUID, data) -> Transaction:
    account = await get_owned_account(session, user_id, data.account_id)
    ensure_account_active(account)
    category = await get_visible_category(session, user_id, data.category_id)
    amount = quantize_money(data.amount)
    transaction = Transaction(
        user_id=user_id,
        account_id=account.id,
        category_id=category.id,
        category_name_snapshot=category.name,
        amount=amount,
        currency=account.currency,
        type=data.type,
        description=data.description,
    )
    apply_transaction_effect(account, amount, data.type)
    session.add(transaction)
    await session.commit()
    await session.refresh(transaction)
    return transaction


async def get_owned_transaction(
    session: AsyncSession, user_id: UUID, transaction_id: UUID
) -> Transaction:
    transaction = await session.scalar(
        select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user_id)
    )
    if transaction is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return transaction


async def update_transaction(
    session: AsyncSession, user_id: UUID, transaction_id: UUID, data
) -> Transaction:
    transaction = await get_owned_transaction(session, user_id, transaction_id)
    old_account = await get_owned_account(session, user_id, transaction.account_id)
    reverse_transaction_effect(old_account, transaction.amount, transaction.type)

    account_id = data.account_id or transaction.account_id
    category_id = data.category_id or transaction.category_id
    amount = quantize_money(data.amount if data.amount is not None else transaction.amount)
    transaction_type = data.type or transaction.type

    new_account = await get_owned_account(session, user_id, account_id)
    ensure_account_active(new_account)
    category = await get_visible_category(session, user_id, category_id)
    apply_transaction_effect(new_account, amount, transaction_type)

    transaction.account_id = new_account.id
    transaction.category_id = category.id
    transaction.category_name_snapshot = category.name
    transaction.amount = amount
    transaction.currency = new_account.currency
    transaction.type = transaction_type
    if "description" in data.model_fields_set:
        transaction.description = data.description
    await session.commit()
    await session.refresh(transaction)
    return transaction


async def delete_transaction(session: AsyncSession, user_id: UUID, transaction_id: UUID) -> None:
    transaction = await get_owned_transaction(session, user_id, transaction_id)
    account = await get_owned_account(session, user_id, transaction.account_id)
    reverse_transaction_effect(account, transaction.amount, transaction.type)
    await session.delete(transaction)
    await session.commit()
