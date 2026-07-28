from uuid import UUID

from fastapi import APIRouter, Response, status

from app.core.security import CurrentUserDep
from app.db.session import SessionDep
from app.schemas.budget import BudgetCreate, BudgetMonthSummaryRead, BudgetRead, BudgetUpdate
from app.services.budgets import (
    calculate_month_summary,
    create_budget,
    delete_budget,
    list_budgets,
    update_budget,
)

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("")
async def list_my_budgets(session: SessionDep, current_user: CurrentUserDep) -> list[BudgetRead]:
    budgets = await list_budgets(session, current_user.id)
    return [BudgetRead.model_validate(budget, from_attributes=True) for budget in budgets]


@router.get("/month-summary")
async def get_my_budget_month_summary(
    session: SessionDep, current_user: CurrentUserDep
) -> list[BudgetMonthSummaryRead]:
    summaries = await calculate_month_summary(session, current_user.id)
    return [BudgetMonthSummaryRead.model_validate(item) for item in summaries]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_my_budget(
    payload: BudgetCreate, session: SessionDep, current_user: CurrentUserDep
) -> BudgetRead:
    budget = await create_budget(session, current_user.id, payload)
    return BudgetRead.model_validate(budget, from_attributes=True)


@router.patch("/{budget_id}")
async def update_my_budget(
    budget_id: UUID, payload: BudgetUpdate, session: SessionDep, current_user: CurrentUserDep
) -> BudgetRead:
    budget = await update_budget(session, current_user.id, budget_id, payload)
    return BudgetRead.model_validate(budget, from_attributes=True)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_budget(
    budget_id: UUID, session: SessionDep, current_user: CurrentUserDep
) -> Response:
    await delete_budget(session, current_user.id, budget_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
