from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.security import CurrentUserDep
from app.db.session import SessionDep
from app.schemas.activity import ActivityFeed
from app.services.activity import get_activity_feed

router = APIRouter(tags=["activity"])

LimitQuery = Annotated[int, Query(ge=1, le=100)]
CursorQuery = Annotated[str | None, Query()]


@router.get("/activity")
async def list_activity(
    session: SessionDep,
    current_user: CurrentUserDep,
    limit: LimitQuery = 50,
    cursor: CursorQuery = None,
) -> ActivityFeed:
    return await get_activity_feed(session, current_user.id, limit, cursor)


@router.get("/accounts/{account_id}/activity")
async def list_account_activity(
    account_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    limit: LimitQuery = 50,
    cursor: CursorQuery = None,
) -> ActivityFeed:
    return await get_activity_feed(session, current_user.id, limit, cursor, account_id=account_id)
