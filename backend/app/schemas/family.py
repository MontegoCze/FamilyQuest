from uuid import UUID

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

    model_config = {"from_attributes": True}
