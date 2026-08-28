from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.enums import Currency
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.models.user import User
from app.schemas.common import quantize_money
from app.services.categories import get_visible_category
from app.services.exchange_rates import get_exchange_rate
from app.services.net_worth_history import capture_net_worth_snapshot


async def get_owned_account(
    session: AsyncSession, user_id: UUID, account_id: UUID, *, for_update: bool = False
) -> Account:
    stmt = select(Account).where(Account.id == account_id, Account.user_id == user_id)
    if for_update:
        stmt = stmt.with_for_update()
    account = await session.scalar(stmt)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


async def get_owned_accounts_locked(
    session: AsyncSession, user_id: UUID, account_ids: list[UUID]
) -> dict[UUID, Account]:
    """Lock owned accounts FOR UPDATE in deterministic id order to avoid deadlocks."""
    unique_ids = sorted(set(account_ids))
    accounts = list(
        await session.scalars(
            select(Account)
            .where(Account.user_id == user_id, Account.id.in_(unique_ids))
            .order_by(Account.id)
            .with_for_update()
        )
    )
    if len(accounts) != len(unique_ids):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Account not found")
    return {account.id: account for account in accounts}


def ensure_account_active(account: Account) -> None:
    if account.archived_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Archived account cannot be used")


async def create_account(session: AsyncSession, user_id: UUID, data) -> Account:
    opening_balance = quantize_money(data.opening_balance)
    account = Account(
        user_id=user_id,
        name=data.name.strip(),
        currency=data.currency,
        opening_balance=opening_balance,
        balance=opening_balance,
        rate_type=data.rate_type,
    )
    session.add(account)
    await capture_net_worth_snapshot(session, user_id)
    await session.commit()
    await session.refresh(account)
    return account


async def list_accounts(
    session: AsyncSession, user_id: UUID, include_archived: bool
) -> list[Account]:
    stmt = select(Account).where(Account.user_id == user_id).order_by(Account.name)
    if not include_archived:
        stmt = stmt.where(Account.archived_at.is_(None))
    return list(await session.scalars(stmt))


async def update_account(session: AsyncSession, user_id: UUID, account_id: UUID, data) -> Account:
    account = await get_owned_account(session, user_id, account_id)
    if data.name is not None:
        account.name = data.name.strip()
    if data.rate_type is not None:
        account.rate_type = data.rate_type
        await capture_net_worth_snapshot(session, user_id)
    await session.commit()
    await session.refresh(account)
    return account


async def archive_account(
    session: AsyncSession, user_id: UUID, account_id: UUID
) -> tuple[Account, list[str]]:
    account = await get_owned_account(session, user_id, account_id)
    if account.archived_at is None:
        account.archived_at = datetime.now(UTC)
    warnings = []
    if account.balance != Decimal("0.00"):
        warnings.append("archived_account_has_non_zero_balance")
    await capture_net_worth_snapshot(session, user_id)
    await session.commit()
    await session.refresh(account)
    return account, warnings


async def delete_account(session: AsyncSession, user_id: UUID, account_id: UUID) -> None:
    account = await get_owned_account(session, user_id, account_id, for_update=True)
    transfers = list(
        await session.scalars(
            select(Transfer)
            .where(
                Transfer.user_id == user_id,
                or_(
                    Transfer.source_account_id == account.id,
                    Transfer.destination_account_id == account.id,
                ),
            )
            .with_for_update()
        )
    )
    counterpart_ids = {
        transfer.destination_account_id
        if transfer.source_account_id == account.id
        else transfer.source_account_id
        for transfer in transfers
    }
    counterparts = list(
        await session.scalars(
            select(Account)
            .where(Account.user_id == user_id, Account.id.in_(counterpart_ids))
            .order_by(Account.id)
            .with_for_update()
        )
    )
    counterparts_by_id = {counterpart.id: counterpart for counterpart in counterparts}

    for transfer in transfers:
        if transfer.source_account_id == account.id:
            destination = counterparts_by_id[transfer.destination_account_id]
            destination.balance = quantize_money(destination.balance - transfer.destination_amount)
        else:
            source = counterparts_by_id[transfer.source_account_id]
            source.balance = quantize_money(source.balance + transfer.source_amount)
        await session.delete(transfer)

    await session.execute(delete(Transaction).where(Transaction.account_id == account.id))
    await session.delete(account)
    await session.flush()
    await capture_net_worth_snapshot(session, user_id)
    await session.commit()


async def update_preferences(session: AsyncSession, user: User, data) -> User:
    if "default_account_id" in data.model_fields_set and data.default_account_id is not None:
        account = await get_owned_account(session, user.id, data.default_account_id)
        ensure_account_active(account)
    if "default_category_id" in data.model_fields_set and data.default_category_id is not None:
        await get_visible_category(session, user.id, data.default_category_id)
    if "default_account_id" in data.model_fields_set:
        user.default_account_id = data.default_account_id
    if "default_category_id" in data.model_fields_set:
        user.default_category_id = data.default_category_id
    await session.commit()
    await session.refresh(user)
    return user


async def calculate_net_worth(
    session: AsyncSession, user_id: UUID, include_archived: bool
) -> tuple[Decimal, Decimal]:
    stmt = select(Account).where(Account.user_id == user_id)
    if not include_archived:
        stmt = stmt.where(Account.archived_at.is_(None))
    accounts = list(await session.scalars(stmt))
    total_ars = Decimal("0.00")
    total_usd = Decimal("0.00")
    for account in accounts:
        rate = await get_exchange_rate(session, account.rate_type)
        if account.currency == Currency.ARS:
            total_ars += account.balance
            total_usd += account.balance / rate
        else:
            total_usd += account.balance
            total_ars += account.balance * rate
    return quantize_money(total_ars), quantize_money(total_usd)


async def resolve_account_by_keyword(
    session: AsyncSession, user: User, keyword: str | None
) -> tuple[Account | None, bool]:
    if keyword:
        matches = list(
            await session.scalars(
                select(Account).where(
                    Account.user_id == user.id,
                    Account.archived_at.is_(None),
                    Account.name.ilike(f"%{keyword}%"),
                )
            )
        )
        if len(matches) == 1:
            return matches[0], False
        if len(matches) > 1:
            return None, True
    if user.default_account_id is None:
        return None, False
    return await get_owned_account(session, user.id, user.default_account_id), True


async def user_has_any_account(session: AsyncSession, user_id: UUID) -> bool:
    return bool(
        await session.scalar(
            select(Account.id).where(
                Account.user_id == user_id,
                or_(Account.archived_at.is_(None), Account.archived_at.is_not(None)),
            )
        )
    )
