from uuid import UUID

from fastapi import APIRouter, Response, status

from app.core.security import CurrentUserDep
from app.db.session import SessionDep
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.services.categories import (
    create_category,
    delete_category,
    list_categories,
    update_category,
)

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
async def list_my_categories(
    session: SessionDep, current_user: CurrentUserDep
) -> list[CategoryRead]:
    categories = await list_categories(session, current_user.id)
    return [CategoryRead.model_validate(category, from_attributes=True) for category in categories]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_my_category(
    payload: CategoryCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> CategoryRead:
    category = await create_category(session, current_user.id, payload.name)
    return CategoryRead.model_validate(category, from_attributes=True)


@router.patch("/{category_id}")
async def update_my_category(
    category_id: UUID,
    payload: CategoryUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> CategoryRead:
    category = await update_category(session, current_user.id, category_id, payload.name)
    return CategoryRead.model_validate(category, from_attributes=True)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_category(
    category_id: UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    await delete_category(session, current_user.id, category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
