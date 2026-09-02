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

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


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


class SwitchAccountResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    impersonated_user_id: str
    impersonated_user_name: str
    impersonated_by_user_id: str
