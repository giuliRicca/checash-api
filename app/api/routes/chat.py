from fastapi import APIRouter

from app.core.security import CurrentUserDep
from app.db.session import SessionDep
from app.models.transfer import Transfer
from app.schemas.chat import ChatConfirmRequest, ChatDraft, ParseMessageRequest
from app.schemas.transaction import TransactionRead
from app.schemas.transfer import TransferRead
from app.services.chat import confirm_draft, parse_message

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/parse-message")
async def parse_chat_message(
    payload: ParseMessageRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ChatDraft:
    return await parse_message(session, current_user, payload.message)


@router.post("/confirm")
async def confirm_chat_draft(
    payload: ChatConfirmRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> TransactionRead | TransferRead:
    record = await confirm_draft(session, current_user, payload.draft)
    if isinstance(record, Transfer):
        return TransferRead.model_validate(record, from_attributes=True)
    return TransactionRead.model_validate(record, from_attributes=True)
