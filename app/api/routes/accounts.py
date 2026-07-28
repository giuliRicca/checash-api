from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.core.security import CurrentUserDep
from app.db.session import SessionDep
from app.schemas.account import (
    AccountAdjustmentCreate,
    AccountArchiveResponse,
    AccountCreate,
    AccountRead,
    AccountUpdate,
    NetWorthHistoryRead,
    NetWorthRead,
)
from app.schemas.transaction import TransactionRead
from app.services.accounts import (
    archive_account,
    calculate_net_worth,
    create_account,
    delete_account,
    get_owned_account,
    list_accounts,
    update_account,
)
from app.services.net_worth_history import get_current_month_history
from app.services.transactions import create_balance_adjustment

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("")
async def create_my_account(
    payload: AccountCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> AccountRead:
    account = await create_account(session, current_user.id, payload)
    return AccountRead.model_validate(account, from_attributes=True)


@router.get("")
async def list_my_accounts(
    session: SessionDep,
    current_user: CurrentUserDep,
    include_archived: bool = False,
) -> list[AccountRead]:
    accounts = await list_accounts(session, current_user.id, include_archived)
    return [AccountRead.model_validate(account, from_attributes=True) for account in accounts]


@router.get("/net-worth")
async def get_net_worth(
    session: SessionDep,
    current_user: CurrentUserDep,
    include_archived: bool = Query(default=False),
) -> NetWorthRead:
    total_ars, total_usd = await calculate_net_worth(session, current_user.id, include_archived)
    return NetWorthRead(total_ars=total_ars, total_usd=total_usd)


@router.get("/net-worth/history")
async def get_my_net_worth_history(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> NetWorthHistoryRead:
    return NetWorthHistoryRead.model_validate(
        await get_current_month_history(session, current_user.id)
    )


@router.get("/{account_id}")
async def get_my_account(
    account_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> AccountRead:
    account = await get_owned_account(session, current_user.id, account_id)
    return AccountRead.model_validate(account, from_attributes=True)


@router.patch("/{account_id}")
async def update_my_account(
    account_id: UUID,
    payload: AccountUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> AccountRead:
    account = await update_account(session, current_user.id, account_id, payload)
    return AccountRead.model_validate(account, from_attributes=True)


@router.post("/{account_id}/adjustments", status_code=201)
async def create_my_account_adjustment(
    account_id: UUID,
    payload: AccountAdjustmentCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TransactionRead:
    transaction = await create_balance_adjustment(session, current_user.id, account_id, payload)
    return TransactionRead.model_validate(transaction, from_attributes=True)


@router.post("/{account_id}/archive")
async def archive_my_account(
    account_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> AccountArchiveResponse:
    account, warnings = await archive_account(session, current_user.id, account_id)
    return AccountArchiveResponse(
        account=AccountRead.model_validate(account, from_attributes=True), warnings=warnings
    )


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    account_id: UUID, session: SessionDep, current_user: CurrentUserDep
) -> Response:
    await delete_account(session, current_user.id, account_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
