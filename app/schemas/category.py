from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import TransactionType


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    type: TransactionType


class CategoryUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class CategoryRead(BaseModel):
    id: UUID
    user_id: UUID | None
    name: str
    slug: str
    type: TransactionType
    is_system: bool
