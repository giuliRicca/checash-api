import re
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.enums import TransactionType
from app.models.transaction import Transaction


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid category name")
    return slug


async def ensure_visible_category_slug_available(
    session: AsyncSession, user_id: UUID, slug: str, exclude_category_id: UUID | None = None
) -> None:
    stmt = select(Category).where(
        Category.slug == slug,
        or_(Category.user_id.is_(None), Category.user_id == user_id),
    )
    if exclude_category_id is not None:
        stmt = stmt.where(Category.id != exclude_category_id)
    if await session.scalar(stmt):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Category slug already exists")


async def get_visible_category(session: AsyncSession, user_id: UUID, category_id: UUID) -> Category:
    category = await session.scalar(
        select(Category).where(
            Category.id == category_id,
            or_(Category.user_id.is_(None), Category.user_id == user_id),
        )
    )
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


async def get_miscellaneous_category(session: AsyncSession) -> Category:
    category = await session.scalar(
        select(Category).where(Category.user_id.is_(None), Category.slug == "miscellaneous")
    )
    if category is None:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Default category missing"
        )
    return category


async def get_fallback_category(
    session: AsyncSession, transaction_type: TransactionType
) -> Category:
    slug = (
        "miscellaneous" if transaction_type == TransactionType.EXPENSE else "uncategorized-income"
    )
    category = await session.scalar(
        select(Category).where(Category.user_id.is_(None), Category.slug == slug)
    )
    if category is None:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Fallback category missing"
        )
    return category


async def list_categories(session: AsyncSession, user_id: UUID) -> list[Category]:
    result = await session.scalars(
        select(Category)
        .where(or_(Category.user_id.is_(None), Category.user_id == user_id))
        .order_by(Category.is_system.desc(), Category.name)
    )
    return list(result)


async def create_category(
    session: AsyncSession, user_id: UUID, name: str, transaction_type: TransactionType
) -> Category:
    slug = slugify(name)
    await ensure_visible_category_slug_available(session, user_id, slug)
    category = Category(
        user_id=user_id, name=name.strip(), slug=slug, type=transaction_type, is_system=False
    )
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


async def update_category(
    session: AsyncSession, user_id: UUID, category_id: UUID, name: str
) -> Category:
    category = await get_visible_category(session, user_id, category_id)
    if category.is_system:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="System categories are immutable")
    slug = slugify(name)
    await ensure_visible_category_slug_available(
        session, user_id, slug, exclude_category_id=category.id
    )
    category.name = name.strip()
    category.slug = slug
    await session.commit()
    await session.refresh(category)
    return category


async def delete_category(session: AsyncSession, user_id: UUID, category_id: UUID) -> None:
    category = await get_visible_category(session, user_id, category_id)
    if category.is_system:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="System categories cannot be deleted")
    is_used = await session.scalar(select(exists().where(Transaction.category_id == category.id)))
    if is_used:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Category is used by transactions")
    await session.execute(delete(Category).where(Category.id == category.id))
    await session.commit()
