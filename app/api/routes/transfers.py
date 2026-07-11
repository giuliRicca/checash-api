from uuid import UUID

from fastapi import APIRouter, Response, status

from app.core.security import CurrentUserDep
from app.db.session import SessionDep
from app.schemas.transfer import TransferCreate, TransferRead, TransferUpdate
from app.services.transfers import create_transfer, delete_transfer, update_transfer

router = APIRouter(prefix="/transfers", tags=["transfers"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_my_transfer(
    payload: TransferCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TransferRead:
    transfer = await create_transfer(session, current_user.id, payload)
    return TransferRead.model_validate(transfer, from_attributes=True)


@router.patch("/{transfer_id}")
async def update_my_transfer(
    transfer_id: UUID,
    payload: TransferUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TransferRead:
    transfer = await update_transfer(session, current_user.id, transfer_id, payload)
    return TransferRead.model_validate(transfer, from_attributes=True)


@router.delete("/{transfer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_transfer(
    transfer_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    await delete_transfer(session, current_user.id, transfer_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
