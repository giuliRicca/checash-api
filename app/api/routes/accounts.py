from uuid import UUID

from fastapi import APIRouter, Query

from app.core.security import CurrentUserDep
from app.db.session import SessionDep
from app.schemas.account import (
    AccountArchiveResponse,
    AccountCreate,
    AccountRead,
    AccountUpdate,
    NetWorthRead,
)
from app.services.accounts import (
    archive_account,
    calculate_net_worth,
    create_account,
    get_owned_account,
    list_accounts,
    update_account,
)

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
