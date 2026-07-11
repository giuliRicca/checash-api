from fastapi import APIRouter

from app.core.security import CurrentUserDep
from app.db.session import SessionDep
from app.schemas.user import UserPreferencesRead, UserPreferencesUpdate
from app.services.accounts import update_preferences

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me/preferences")
async def update_my_preferences(
    payload: UserPreferencesUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> UserPreferencesRead:
    user = await update_preferences(session, current_user, payload)
    return UserPreferencesRead(
        default_account_id=user.default_account_id,
        default_category_id=user.default_category_id,
    )
