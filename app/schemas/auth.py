from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth token type, not a password.


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str | None
    default_account_id: UUID | None
    default_category_id: UUID | None
