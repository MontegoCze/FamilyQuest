from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_parent
from app.crud.family import create_family, get_family_for_user, list_family_members
from app.database import get_db
from app.models.familyquest import FamilyMember, User
from app.schemas.family import FamilyCreate, FamilyMemberRead, FamilyRead

router = APIRouter()


@router.get("", response_model=FamilyRead | None)
def get_family(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    family = get_family_for_user(db, current_user.id)
    if not family:
        return None
    return family


@router.post("", response_model=FamilyRead, status_code=status.HTTP_201_CREATED)
def create_user_family(
    payload: FamilyCreate,
    current_user: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    if get_family_for_user(db, current_user.id):
        raise HTTPException(status_code=400, detail="Current user already belongs to a family.")
    family = create_family(db, name=payload.name, parent_user=current_user)
    return family


@router.get("/members", response_model=list[FamilyMemberRead])
def list_members(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    family = get_family_for_user(db, current_user.id)
    if not family:
        raise HTTPException(status_code=404, detail="Family not found for this user.")
    members = list_family_members(db, family.id)
    return members
