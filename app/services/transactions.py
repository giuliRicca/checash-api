from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.enums import Currency, RateType, TransactionType
from app.models.transaction import Transaction
from app.schemas.common import quantize_money
from app.services.accounts import ensure_account_active, get_owned_account
from app.services.categories import (
    get_balance_adjustment_category,
    get_visible_category,
    is_balance_adjustment_category,
)
from app.services.exchange_rates import get_exchange_rate
from app.services.net_worth_history import capture_net_worth_snapshot


def get_current_month_window() -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1)
    return month_start, month_end


def apply_transaction_effect(
    account: Account, account_amount: Decimal, transaction_type: TransactionType
) -> None:
    if transaction_type == TransactionType.EXPENSE:
        account.balance = quantize_money(account.balance - account_amount)
    else:
        account.balance = quantize_money(account.balance + account_amount)


def reverse_transaction_effect(
    account: Account, account_amount: Decimal, transaction_type: TransactionType
) -> None:
    if transaction_type == TransactionType.EXPENSE:
        account.balance = quantize_money(account.balance + account_amount)
    else:
        account.balance = quantize_money(account.balance - account_amount)


def calculate_account_amount(
    amount: Decimal, transaction_currency: Currency, account_currency: Currency, rate: Decimal
) -> Decimal:
    if transaction_currency == account_currency:
        return amount
    if transaction_currency == Currency.USD:
        return quantize_money(amount * rate)
    return quantize_money(amount / rate)


async def create_transaction(session: AsyncSession, user_id: UUID, data) -> Transaction:
    account = await get_owned_account(session, user_id, data.account_id, for_update=True)
    ensure_account_active(account)
    category = await get_visible_category(session, user_id, data.category_id)
    if is_balance_adjustment_category(category):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Balance adjustments must use the account adjustment endpoint",
        )
    if category.type != data.type:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Category type must match transaction type",
        )
    amount = quantize_money(data.amount)
    currency = data.currency or account.currency
    rate_used = await get_exchange_rate(session, account.rate_type)
    account_amount = calculate_account_amount(amount, currency, account.currency, rate_used)
    transaction = Transaction(
        user_id=user_id,
        account_id=account.id,
        category_id=category.id,
        category_name_snapshot=category.name,
        amount=amount,
        account_amount=account_amount,
        currency=currency,
        rate_used=rate_used,
        type=data.type,
        description=data.description,
        occurred_at=data.occurred_at or datetime.now(UTC),
    )
    apply_transaction_effect(account, account_amount, data.type)
    session.add(transaction)
    await capture_net_worth_snapshot(session, user_id)
    await session.commit()
    await session.refresh(transaction)
    return transaction


async def create_balance_adjustment(
    session: AsyncSession, user_id: UUID, account_id: UUID, data
) -> Transaction:
    account = await get_owned_account(session, user_id, account_id, for_update=True)
    ensure_account_active(account)
    target_balance = quantize_money(data.target_balance)
    delta = quantize_money(target_balance - account.balance)
    if delta == Decimal("0.00"):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Target balance must differ from current balance",
        )

    transaction_type = TransactionType.INCOME if delta > 0 else TransactionType.EXPENSE
    category = await get_balance_adjustment_category(session, transaction_type)
    transaction = Transaction(
        user_id=user_id,
        account_id=account.id,
        category_id=category.id,
        category_name_snapshot=category.name,
        amount=abs(delta),
        account_amount=abs(delta),
        currency=account.currency,
        is_adjustment=True,
        type=transaction_type,
        description=data.description,
        occurred_at=data.occurred_at or datetime.now(UTC),
    )
    apply_transaction_effect(account, transaction.account_amount, transaction.type)
    session.add(transaction)
    await capture_net_worth_snapshot(session, user_id)
    await session.commit()
    await session.refresh(transaction)
    return transaction


async def calculate_month_summary(session: AsyncSession, user_id: UUID) -> dict:
    month_start, month_end = get_current_month_window()
    rows = list(
        await session.execute(
            select(Transaction, Account)
            .join(Account, Account.id == Transaction.account_id)
            .where(
                Transaction.user_id == user_id,
                Transaction.occurred_at >= month_start,
                Transaction.occurred_at < month_end,
            )
        )
    )

    rates: dict[RateType, Decimal] = {}
    totals = {
        "income_ars": Decimal("0.00"),
        "income_usd": Decimal("0.00"),
        "expense_ars": Decimal("0.00"),
        "expense_usd": Decimal("0.00"),
    }

    for transaction, account in rows:
        if transaction.is_adjustment:
            continue
        rate = transaction.rate_used or rates.get(account.rate_type)
        if rate is None:
            rate = await get_exchange_rate(session, account.rate_type)
            rates[account.rate_type] = rate

        if transaction.currency == Currency.ARS:
            amount_ars = transaction.amount
            amount_usd = transaction.amount / rate
        else:
            amount_usd = transaction.amount
            amount_ars = transaction.amount * rate

        prefix = "income" if transaction.type == TransactionType.INCOME else "expense"
        totals[f"{prefix}_ars"] += amount_ars
        totals[f"{prefix}_usd"] += amount_usd

    return {
        "month_start": month_start,
        "month_end": month_end,
        "income_ars": quantize_money(totals["income_ars"]),
        "income_usd": quantize_money(totals["income_usd"]),
        "expense_ars": quantize_money(totals["expense_ars"]),
        "expense_usd": quantize_money(totals["expense_usd"]),
    }


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
    if transaction.is_adjustment:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Balance adjustments must be changed through the account adjustment flow",
        )

    account_id = data.account_id or transaction.account_id
    category_id = data.category_id or transaction.category_id
    amount = quantize_money(data.amount if data.amount is not None else transaction.amount)
    currency = data.currency if data.currency is not None else transaction.currency

    old_account = await get_owned_account(session, user_id, transaction.account_id, for_update=True)
    new_account = (
        old_account
        if account_id == old_account.id
        else await get_owned_account(session, user_id, account_id, for_update=True)
    )
    ensure_account_active(new_account)
    category = await get_visible_category(session, user_id, category_id)
    if is_balance_adjustment_category(category):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Balance adjustments must use the account adjustment endpoint",
        )
    if category.type != transaction.type:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Category type must match transaction type",
        )
    account_moved = new_account.id != old_account.id
    currency_changed = currency != transaction.currency
    rate_used = transaction.rate_used
    if account_moved or currency_changed:
        rate_used = await get_exchange_rate(session, new_account.rate_type)
    if rate_used is None:
        rate_used = await get_exchange_rate(session, new_account.rate_type)
    account_amount = calculate_account_amount(amount, currency, new_account.currency, rate_used)

    reverse_transaction_effect(old_account, transaction.account_amount, transaction.type)
    apply_transaction_effect(new_account, account_amount, transaction.type)

    transaction.account_id = new_account.id
    transaction.category_id = category.id
    transaction.category_name_snapshot = category.name
    transaction.amount = amount
    transaction.account_amount = account_amount
    transaction.currency = currency
    transaction.rate_used = rate_used
    if "description" in data.model_fields_set:
        transaction.description = data.description
    if "occurred_at" in data.model_fields_set and data.occurred_at is not None:
        transaction.occurred_at = data.occurred_at
    await capture_net_worth_snapshot(session, user_id)
    await session.commit()
    await session.refresh(transaction)
    return transaction


async def delete_transaction(session: AsyncSession, user_id: UUID, transaction_id: UUID) -> None:
    transaction = await get_owned_transaction(session, user_id, transaction_id)
    if transaction.is_adjustment:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Balance adjustments must be changed through the account adjustment flow",
        )
    account = await get_owned_account(session, user_id, transaction.account_id, for_update=True)
    reverse_transaction_effect(account, transaction.account_amount, transaction.type)
    await session.delete(transaction)
    await capture_net_worth_snapshot(session, user_id)
    await session.commit()
