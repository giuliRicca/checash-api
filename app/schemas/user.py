from uuid import UUID

from pydantic import BaseModel


class UserPreferencesUpdate(BaseModel):
    default_account_id: UUID | None = None
    default_category_id: UUID | None = None


class UserPreferencesRead(BaseModel):
    default_account_id: UUID | None
    default_category_id: UUID | None
