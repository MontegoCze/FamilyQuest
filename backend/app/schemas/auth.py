from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=120)
    role: Literal["parent"] = "parent"

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower()


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserAvatarUpdate(BaseModel):
    avatar: str = Field(..., min_length=1, max_length=20)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str
    avatar: str | None = None
    is_active: bool = True

    model_config = {"from_attributes": True}
