from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserProfileUpdate(BaseModel):
    email: EmailStr
    display_name: str | None = Field(default=None, max_length=120)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class UserPreferencesUpdate(BaseModel):
    default_account_id: UUID | None = None
    default_category_id: UUID | None = None


class UserPreferencesRead(BaseModel):
    default_account_id: UUID | None
    default_category_id: UUID | None
