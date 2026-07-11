from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.enums import Currency
from app.models.transfer import Transfer
from app.schemas.common import quantize_money, quantize_rate
from app.services.accounts import ensure_account_active, get_owned_account
from app.services.exchange_rates import get_exchange_rate


async def calculate_destination_amount(
    session: AsyncSession,
    source: Account,
    destination: Account,
    source_amount: Decimal,
    rate_override: Decimal | None,
) -> tuple[Decimal, Decimal | None]:
    if source.currency == destination.currency:
        return source_amount, None

    rate = (
        quantize_rate(rate_override)
        if rate_override is not None
        else await get_exchange_rate(session, destination.rate_type)
    )
    if source.currency == Currency.USD and destination.currency == Currency.ARS:
        return quantize_money(source_amount * rate), rate
    return quantize_money(source_amount / rate), rate


def apply_transfer_effect(source: Account, destination: Account, transfer: Transfer) -> None:
    source.balance = quantize_money(source.balance - transfer.source_amount)
    destination.balance = quantize_money(destination.balance + transfer.destination_amount)


def reverse_transfer_effect(source: Account, destination: Account, transfer: Transfer) -> None:
    source.balance = quantize_money(source.balance + transfer.source_amount)
    destination.balance = quantize_money(destination.balance - transfer.destination_amount)


async def create_transfer(session: AsyncSession, user_id: UUID, data) -> Transfer:
    if data.source_account_id == data.destination_account_id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Accounts must be distinct"
        )
    source = await get_owned_account(session, user_id, data.source_account_id)
    destination = await get_owned_account(session, user_id, data.destination_account_id)
    ensure_account_active(source)
    ensure_account_active(destination)
    source_amount = quantize_money(data.source_amount)
    destination_amount, rate = await calculate_destination_amount(
        session, source, destination, source_amount, data.rate_override
    )
    transfer = Transfer(
        user_id=user_id,
        source_account_id=source.id,
        destination_account_id=destination.id,
        source_amount=source_amount,
        source_currency=source.currency,
        destination_amount=destination_amount,
        destination_currency=destination.currency,
        rate_used=rate,
        description=data.description,
    )
    apply_transfer_effect(source, destination, transfer)
    session.add(transfer)
    await session.commit()
    await session.refresh(transfer)
    return transfer


async def get_owned_transfer(session: AsyncSession, user_id: UUID, transfer_id: UUID) -> Transfer:
    transfer = await session.scalar(
        select(Transfer).where(Transfer.id == transfer_id, Transfer.user_id == user_id)
    )
    if transfer is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Transfer not found")
    return transfer


async def update_transfer(
    session: AsyncSession, user_id: UUID, transfer_id: UUID, data
) -> Transfer:
    transfer = await get_owned_transfer(session, user_id, transfer_id)
    old_source = await get_owned_account(session, user_id, transfer.source_account_id)
    old_destination = await get_owned_account(session, user_id, transfer.destination_account_id)
    reverse_transfer_effect(old_source, old_destination, transfer)

    source_id = data.source_account_id or transfer.source_account_id
    destination_id = data.destination_account_id or transfer.destination_account_id
    if source_id == destination_id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Accounts must be distinct"
        )
    source = await get_owned_account(session, user_id, source_id)
    destination = await get_owned_account(session, user_id, destination_id)
    ensure_account_active(source)
    ensure_account_active(destination)
    source_amount = quantize_money(
        data.source_amount if data.source_amount is not None else transfer.source_amount
    )
    destination_amount, rate = await calculate_destination_amount(
        session, source, destination, source_amount, data.rate_override
    )

    transfer.source_account_id = source.id
    transfer.destination_account_id = destination.id
    transfer.source_amount = source_amount
    transfer.source_currency = source.currency
    transfer.destination_amount = destination_amount
    transfer.destination_currency = destination.currency
    transfer.rate_used = rate
    if "description" in data.model_fields_set:
        transfer.description = data.description
    apply_transfer_effect(source, destination, transfer)
    await session.commit()
    await session.refresh(transfer)
    return transfer


async def delete_transfer(session: AsyncSession, user_id: UUID, transfer_id: UUID) -> None:
    transfer = await get_owned_transfer(session, user_id, transfer_id)
    source = await get_owned_account(session, user_id, transfer.source_account_id)
    destination = await get_owned_account(session, user_id, transfer.destination_account_id)
    reverse_transfer_effect(source, destination, transfer)
    await session.delete(transfer)
    await session.commit()
