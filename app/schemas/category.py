from uuid import UUID

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class CategoryUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class CategoryRead(BaseModel):
    id: UUID
    user_id: UUID | None
    name: str
    slug: str
    is_system: bool
