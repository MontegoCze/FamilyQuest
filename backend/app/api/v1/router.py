from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.v1.auth import router as auth_router
from app.api.v1.family import router as family_router
from app.api.v1.quest import router as quest_router
from app.models.familyquest import User
from app.schemas.auth import UserRead

api_router = APIRouter()


@api_router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(family_router, prefix="/family", tags=["family"])
api_router.include_router(quest_router, tags=["familyquest"])
