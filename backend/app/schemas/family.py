from datetime import datetime

from pydantic import BaseModel, Field


class FamilyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)


class FamilyRead(BaseModel):
    id: str
    name: str

    model_config = {"from_attributes": True}


class FamilyMemberRead(BaseModel):
    id: str
    user_id: str
    family_id: str
    role: str
    full_name: str | None = None
    email: str | None = None
    avatar: str | None = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class FamilyMemberCreate(BaseModel):
    role: str = Field(..., pattern="^(child|parent)$")
    full_name: str = Field(..., min_length=2, max_length=120)
    email: str | None = Field(default=None, min_length=3, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class FamilyMemberUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    avatar: str | None = Field(default=None, max_length=20)


class FamilyInvitationCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., min_length=3, max_length=255)


class FamilyInvitationRead(BaseModel):
    id: str
    family_id: str
    invited_email: str
    invited_name: str
    token: str
    status: str
    expires_at: datetime

    model_config = {"from_attributes": True}
