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


async def update_user_profile(
    session: AsyncSession, user: User, email: str, display_name: str | None
) -> User:
    normalized_email = normalize_email(email)
    existing_user = await session.scalar(
        select(User).where(User.email == normalized_email, User.id != user.id)
    )
    if existing_user is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")

    user.email = normalized_email
    user.display_name = display_name.strip() if display_name and display_name.strip() else None
    await session.commit()
    await session.refresh(user)
    return user


async def change_user_password(
    session: AsyncSession, user: User, current_password: str, new_password: str
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    user.password_hash = hash_password(new_password)
    await session.commit()
