from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.budget import Budget
from app.models.category import Category
from app.models.enums import Currency, RateType, TransactionType
from app.models.transaction import Transaction
from app.schemas.budget import BudgetCreate, BudgetUpdate
from app.schemas.common import quantize_money
from app.services.categories import get_visible_category, is_balance_adjustment_category
from app.services.exchange_rates import get_exchange_rate
from app.services.transactions import get_current_month_window


async def ensure_budget_category(
    session: AsyncSession, user_id: UUID, category_id: UUID
) -> Category:
    category = await get_visible_category(session, user_id, category_id)
    if category.type != TransactionType.EXPENSE:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Budget category must be expense"
        )
    if is_balance_adjustment_category(category):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Balance adjustment category cannot have a budget",
        )
    return category


async def list_budgets(session: AsyncSession, user_id: UUID) -> list[Budget]:
    result = await session.scalars(
        select(Budget).where(Budget.user_id == user_id).order_by(Budget.created_at)
    )
    return list(result)


async def create_budget(session: AsyncSession, user_id: UUID, data: BudgetCreate) -> Budget:
    await ensure_budget_category(session, user_id, data.category_id)
    budget = Budget(
        user_id=user_id,
        category_id=data.category_id,
        amount=quantize_money(data.amount),
        currency=data.currency,
    )
    session.add(budget)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Budget already exists for category"
        ) from exc
    await session.refresh(budget)
    return budget


async def get_owned_budget(session: AsyncSession, user_id: UUID, budget_id: UUID) -> Budget:
    budget = await session.scalar(
        select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
    )
    if budget is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return budget


async def update_budget(
    session: AsyncSession, user_id: UUID, budget_id: UUID, data: BudgetUpdate
) -> Budget:
    budget = await get_owned_budget(session, user_id, budget_id)
    if data.category_id is not None:
        await ensure_budget_category(session, user_id, data.category_id)
        budget.category_id = data.category_id
    if data.amount is not None:
        budget.amount = quantize_money(data.amount)
    if data.currency is not None:
        budget.currency = data.currency
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Budget already exists for category"
        ) from exc
    await session.refresh(budget)
    return budget


async def delete_budget(session: AsyncSession, user_id: UUID, budget_id: UUID) -> None:
    await session.delete(await get_owned_budget(session, user_id, budget_id))
    await session.commit()


async def calculate_month_summary(session: AsyncSession, user_id: UUID) -> list[dict]:
    budget_rows = list(
        await session.execute(
            select(Budget, Category.name)
            .join(Category, Category.id == Budget.category_id)
            .where(Budget.user_id == user_id)
        )
    )
    if not budget_rows:
        return []
    month_start, month_end = get_current_month_window()
    category_ids = [budget.category_id for budget, _ in budget_rows]
    expenses = list(
        await session.execute(
            select(Transaction, Account)
            .join(Account, Account.id == Transaction.account_id)
            .where(
                Transaction.user_id == user_id,
                Transaction.category_id.in_(category_ids),
                Transaction.type == TransactionType.EXPENSE,
                Transaction.is_adjustment.is_(False),
                Transaction.occurred_at >= month_start,
                Transaction.occurred_at < month_end,
            )
        )
    )
    by_category: dict[UUID, list[tuple[Transaction, Account]]] = {}
    for transaction, account in expenses:
        by_category.setdefault(transaction.category_id, []).append((transaction, account))
    rates: dict[RateType, Decimal] = {}
    summaries: list[dict] = []
    for budget, category_name in budget_rows:
        spent = Decimal("0.00")
        for transaction, account in by_category.get(budget.category_id, []):
            amount = transaction.amount
            if transaction.currency != budget.currency:
                rate = transaction.rate_used or rates.get(account.rate_type)
                if rate is None:
                    rate = await get_exchange_rate(session, account.rate_type)
                    rates[account.rate_type] = rate
                amount = amount / rate if budget.currency == Currency.USD else amount * rate
            spent += amount
        spent = quantize_money(spent)
        remaining = quantize_money(budget.amount - spent)
        percentage = (spent / budget.amount * Decimal("100")).quantize(Decimal("0.01"))
        summaries.append(
            {
                "id": budget.id,
                "category_id": budget.category_id,
                "amount": budget.amount,
                "currency": budget.currency,
                "created_at": budget.created_at,
                "category_name": category_name,
                "spent": spent,
                "remaining": remaining,
                "percentage": percentage,
                "status": (
                    "over_budget"
                    if spent > budget.amount
                    else "at_limit"
                    if spent == budget.amount
                    else "on_track"
                ),
            }
        )
    return summaries
