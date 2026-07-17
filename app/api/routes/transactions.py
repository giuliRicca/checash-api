from uuid import UUID

from fastapi import APIRouter, Response, status

from app.core.security import CurrentUserDep
from app.db.session import SessionDep
from app.schemas.transaction import (
    TransactionCreate,
    TransactionMonthSummaryRead,
    TransactionRead,
    TransactionUpdate,
)
from app.services.transactions import (
    calculate_month_summary,
    create_transaction,
    delete_transaction,
    update_transaction,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_my_transaction(
    payload: TransactionCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TransactionRead:
    transaction = await create_transaction(session, current_user.id, payload)
    return TransactionRead.model_validate(transaction, from_attributes=True)


@router.get("/month-summary")
async def get_my_month_summary(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TransactionMonthSummaryRead:
    return TransactionMonthSummaryRead.model_validate(
        await calculate_month_summary(session, current_user.id)
    )


@router.patch("/{transaction_id}")
async def update_my_transaction(
    transaction_id: UUID,
    payload: TransactionUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TransactionRead:
    transaction = await update_transaction(session, current_user.id, transaction_id, payload)
    return TransactionRead.model_validate(transaction, from_attributes=True)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_transaction(
    transaction_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    await delete_transaction(session, current_user.id, transaction_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
