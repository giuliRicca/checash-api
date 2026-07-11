import re
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.enums import Currency, TransactionType
from app.models.user import User
from app.schemas.chat import ChatDraft, ExchangeDetailsDraft
from app.schemas.transaction import TransactionCreate
from app.schemas.transfer import TransferCreate
from app.services.accounts import resolve_account_by_keyword
from app.services.categories import get_visible_category
from app.services.transactions import create_transaction
from app.services.transfers import create_transfer


async def parse_message(session: AsyncSession, user: User, message: str) -> ChatDraft:
    lowered = message.strip().lower()
    amount = extract_amount(lowered)
    if amount is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Could not parse amount")

    is_exchange = any(word in lowered for word in ["transfer", "transferi", "cambie", "cambié"])
    transaction_type: TransactionType | str = (
        "transfer" if is_exchange else infer_transaction_type(lowered)
    )
    currency, currency_guessed = infer_currency(lowered)
    account_keyword = extract_keyword(lowered, ["desde", "con", "de"])
    account, account_guessed = await resolve_account_by_keyword(session, user, account_keyword)
    if account is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Could not resolve account"
        )
    if currency is None:
        currency = account.currency
        currency_guessed = True

    category, category_guessed = await resolve_category(session, user, lowered)
    destination_keyword = extract_keyword(lowered, ["a", "hacia"])
    destination_account = None
    ambiguous_destination = False
    if is_exchange:
        destination_account, ambiguous_destination = await resolve_account_by_keyword(
            session, user, destination_keyword
        )

    exchange_details = None
    if is_exchange:
        exchange_details = ExchangeDetailsDraft(
            destination_currency=destination_account.currency if destination_account else None,
            destination_account_keyword=destination_keyword,
            destination_account_id=destination_account.id if destination_account else None,
        )

    return ChatDraft(
        amount=amount,
        currency=currency,
        account_keyword=account_keyword,
        account_id=account.id,
        category_id=category.id if category else None,
        category_name=category.name if category else None,
        transaction_type=transaction_type,
        description=message.strip(),
        is_exchange=is_exchange,
        exchange_details=exchange_details,
        needs_review=currency_guessed
        or account_guessed
        or category_guessed
        or ambiguous_destination,
    )


def extract_amount(message: str) -> Decimal | None:
    match = re.search(r"\b(\d+(?:[\.,]\d{1,2})?)\b", message)
    if not match:
        return None
    return Decimal(match.group(1).replace(",", "."))


def infer_currency(message: str) -> tuple[Currency | None, bool]:
    if re.search(r"\b(usd|dolares|dólares|u\$s)\b", message):
        return Currency.USD, False
    if re.search(r"\b(ars|pesos|\$)\b", message):
        return Currency.ARS, False
    return None, True


def infer_transaction_type(message: str) -> TransactionType:
    if any(word in message for word in ["cobre", "cobré", "ingrese", "ingresé", "salario"]):
        return TransactionType.INCOME
    return TransactionType.EXPENSE


def extract_keyword(message: str, markers: list[str]) -> str | None:
    for marker in markers:
        match = re.search(rf"\b{marker}\s+([a-z0-9áéíóúñ ]+)\b", message)
        if match:
            return match.group(1).strip()
    return None


async def resolve_category(
    session: AsyncSession, user: User, message: str
) -> tuple[Category | None, bool]:
    categories = list(
        await session.scalars(
            select(Category).where(or_(Category.user_id.is_(None), Category.user_id == user.id))
        )
    )
    matches = [
        category
        for category in categories
        if category.slug in message or category.name.lower() in message
    ]
    if len(matches) == 1:
        return matches[0], False
    if user.default_category_id is None:
        return None, True
    return await get_visible_category(session, user.id, user.default_category_id), True


async def confirm_draft(session: AsyncSession, user: User, draft: ChatDraft):
    if draft.is_exchange or draft.transaction_type == "transfer":
        if draft.account_id is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Transfer source account is required",
            )
        if draft.exchange_details is None or draft.exchange_details.destination_account_id is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Transfer destination account is required",
            )
        return await create_transfer(
            session,
            user.id,
            TransferCreate(
                source_account_id=draft.account_id,
                destination_account_id=draft.exchange_details.destination_account_id,
                source_amount=draft.amount,
                rate_override=draft.exchange_details.rate_override,
                description=draft.description,
            ),
        )

    if draft.account_id is None or draft.category_id is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Account and category required"
        )
    return await create_transaction(
        session,
        user.id,
        TransactionCreate(
            account_id=draft.account_id,
            category_id=draft.category_id,
            amount=draft.amount,
            type=TransactionType(draft.transaction_type),
            description=draft.description,
        ),
    )
