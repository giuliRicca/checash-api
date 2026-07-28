from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.enums import Currency, TransactionType
from app.models.net_worth_snapshot import NetWorthSnapshot
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.schemas.common import quantize_money
from app.services.exchange_rates import get_exchange_rate, get_latest_cached_rate


async def capture_net_worth_snapshot(session: AsyncSession, user_id: UUID) -> None:
    accounts = list(
        await session.scalars(
            select(Account).where(Account.user_id == user_id, Account.archived_at.is_(None))
        )
    )
    rates = {}
    for account in accounts:
        rate = rates.get(account.rate_type)
        if rate is None:
            cached_rate = await get_latest_cached_rate(session, account.rate_type)
            if cached_rate is None:
                return
            rates[account.rate_type] = cached_rate.value

    total_ars = sum(
        (
            account.balance
            if account.currency == Currency.ARS
            else account.balance * rates[account.rate_type]
            for account in accounts
        ),
        Decimal("0.00"),
    )
    total_usd = sum(
        (
            account.balance / rates[account.rate_type]
            if account.currency == Currency.ARS
            else account.balance
            for account in accounts
        ),
        Decimal("0.00"),
    )
    session.add(
        NetWorthSnapshot(
            user_id=user_id,
            total_ars=quantize_money(total_ars),
            total_usd=quantize_money(total_usd),
            captured_at=datetime.now(UTC),
        )
    )


def get_current_month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def get_current_month_history(session: AsyncSession, user_id: UUID) -> dict:
    now = datetime.now(UTC)
    month_start = get_current_month_start(now)
    accounts = list(
        await session.scalars(
            select(Account).where(Account.user_id == user_id, Account.archived_at.is_(None))
        )
    )
    if not accounts:
        return {"month_start": month_start.date(), "points": []}

    account_ids = {account.id for account in accounts}
    balances = {account.id: account.balance for account in accounts}
    daily_effects: dict[date, dict[UUID, Decimal]] = defaultdict(
        lambda: defaultdict(lambda: Decimal("0.00"))
    )

    transactions = list(
        await session.scalars(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.account_id.in_(account_ids),
                Transaction.occurred_at >= month_start,
                Transaction.occurred_at <= now,
            )
        )
    )
    for transaction in transactions:
        effect = (
            transaction.account_amount
            if transaction.type == TransactionType.INCOME
            else -transaction.account_amount
        )
        daily_effects[transaction.occurred_at.date()][transaction.account_id] += effect
        balances[transaction.account_id] -= effect

    transfers = list(
        await session.scalars(
            select(Transfer).where(
                Transfer.user_id == user_id,
                Transfer.created_at >= month_start,
                Transfer.created_at <= now,
            )
        )
    )
    for transfer in transfers:
        transfer_day = transfer.created_at.date()
        if transfer.source_account_id in account_ids:
            daily_effects[transfer_day][transfer.source_account_id] -= transfer.source_amount
            balances[transfer.source_account_id] += transfer.source_amount
        if transfer.destination_account_id in account_ids:
            daily_effects[transfer_day][transfer.destination_account_id] += (
                transfer.destination_amount
            )
            balances[transfer.destination_account_id] -= transfer.destination_amount

    for account in accounts:
        if account.created_at >= month_start:
            daily_effects[account.created_at.date()][account.id] += account.opening_balance
            balances[account.id] -= account.opening_balance

    rates = {}
    for account in accounts:
        if account.rate_type not in rates:
            rates[account.rate_type] = await get_exchange_rate(session, account.rate_type)

    points = []
    current_day = month_start.date()
    while current_day <= now.date():
        for account_id, effect in daily_effects[current_day].items():
            balances[account_id] += effect
        total_ars = sum(
            (
                balances[account.id]
                if account.currency == Currency.ARS
                else balances[account.id] * rates[account.rate_type]
                for account in accounts
            ),
            Decimal("0.00"),
        )
        total_usd = sum(
            (
                balances[account.id] / rates[account.rate_type]
                if account.currency == Currency.ARS
                else balances[account.id]
                for account in accounts
            ),
            Decimal("0.00"),
        )
        points.append(
            {
                "date": current_day,
                "total_ars": quantize_money(total_ars),
                "total_usd": quantize_money(total_usd),
            }
        )
        current_day += timedelta(days=1)

    return {"month_start": month_start.date(), "points": points}
