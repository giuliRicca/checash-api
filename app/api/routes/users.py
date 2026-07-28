from fastapi import APIRouter, status

from app.core.security import CurrentUserDep
from app.db.session import SessionDep
from app.schemas.auth import UserRead
from app.schemas.user import (
    PasswordChange,
    UserPreferencesRead,
    UserPreferencesUpdate,
    UserProfileUpdate,
)
from app.services.accounts import update_preferences
from app.services.auth import change_user_password, update_user_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me")
async def update_my_profile(
    payload: UserProfileUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> UserRead:
    user = await update_user_profile(session, current_user, payload.email, payload.display_name)
    return UserRead.model_validate(user, from_attributes=True)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    payload: PasswordChange,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> None:
    await change_user_password(
        session, current_user, payload.current_password, payload.new_password
    )


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
