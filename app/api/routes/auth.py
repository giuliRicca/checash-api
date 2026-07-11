from fastapi import APIRouter, status

from app.core.security import CurrentUserDep
from app.db.session import SessionDep
from app.schemas.auth import TokenResponse, UserLogin, UserRead, UserRegister
from app.services.auth import login_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, session: SessionDep) -> TokenResponse:
    _, token = await register_user(session, payload.email, payload.password)
    return TokenResponse(access_token=token)


@router.post("/login")
async def login(payload: UserLogin, session: SessionDep) -> TokenResponse:
    return TokenResponse(access_token=await login_user(session, payload.email, payload.password))


@router.get("/me")
async def me(current_user: CurrentUserDep) -> UserRead:
    return UserRead.model_validate(current_user, from_attributes=True)
