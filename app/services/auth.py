from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, normalize_email, verify_password
from app.models.user import User
from app.services.categories import get_miscellaneous_category


async def register_user(session: AsyncSession, email: str, password: str) -> tuple[User, str]:
    normalized_email = normalize_email(email)
    if await session.scalar(select(User).where(User.email == normalized_email)):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")

    default_category = await get_miscellaneous_category(session)
    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        default_category_id=default_category.id,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user, create_access_token(user.id)


async def login_user(session: AsyncSession, email: str, password: str) -> str:
    user = await session.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return create_access_token(user.id)
