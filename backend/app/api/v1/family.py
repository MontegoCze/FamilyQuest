from datetime import datetime, timedelta
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_parent
from app.core.security import get_password_hash
from app.crud.family import create_family, get_family_for_user, list_family_members
from app.database import get_db
from app.models.familyquest import FamilyInvitation, FamilyMember, User, UserRole
from app.schemas.family import (
    FamilyCreate, FamilyInvitationCreate, FamilyInvitationRead, FamilyMemberCreate, FamilyMemberRead,
    FamilyMemberUpdate, FamilyRead,
)

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


@router.get("/members/{user_id}", response_model=FamilyMemberRead)
def get_member(user_id: str, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    family = get_family_for_user(db, current_user.id)
    member = db.query(FamilyMember).filter(
        FamilyMember.family_id == family.id if family else "",
        FamilyMember.user_id == user_id,
    ).first() if family else None
    if not member or not member.user.is_active:
        raise HTTPException(status_code=404, detail="Family member not found.")
    return member


@router.post("/members", response_model=FamilyMemberRead, status_code=status.HTTP_201_CREATED)
def add_member(payload: FamilyMemberCreate, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    family = get_family_for_user(db, current_user.id)
    if not family:
        raise HTTPException(status_code=404, detail="Family not found.")
    if payload.role == UserRole.parent.value:
        raise HTTPException(status_code=400, detail="Use the parent invitation endpoint for parent accounts.")
    if payload.role == UserRole.parent.value and not payload.email:
        raise HTTPException(status_code=400, detail="An email is required for a parent account.")
    email = payload.email.lower() if payload.email else f"child-{secrets.token_hex(6)}@familyquest.app"
    if payload.role == UserRole.parent.value and not payload.password:
        raise HTTPException(status_code=400, detail="A password is required for a parent account.")
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        if db.query(FamilyMember).filter(FamilyMember.family_id == family.id, FamilyMember.user_id == existing.id).first():
            raise HTTPException(status_code=409, detail="This user is already a family member.")
        raise HTTPException(status_code=409, detail="This email is already registered. Use a family invitation instead.")
    user = User(email=email, full_name=payload.full_name.strip(), password_hash=get_password_hash(payload.password or secrets.token_urlsafe(16)), role=payload.role, is_active=True)
    db.add(user)
    db.flush()
    member = FamilyMember(family_id=family.id, user_id=user.id, role=payload.role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.post("/invitations", response_model=FamilyInvitationRead, status_code=status.HTTP_201_CREATED)
def invite_parent(payload: FamilyInvitationCreate, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    family = get_family_for_user(db, current_user.id)
    if not family:
        raise HTTPException(status_code=404, detail="Family not found.")
    email = payload.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="This email is already registered.")
    invitation = FamilyInvitation(
        family_id=family.id, invited_email=email, invited_name=payload.full_name.strip(),
        token=secrets.token_urlsafe(32), status="pending", created_by=current_user.id,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


@router.post("/invitations/{token}/accept", response_model=FamilyMemberRead, status_code=status.HTTP_201_CREATED)
def accept_parent_invitation(token: str, payload: FamilyMemberCreate, db: Session = Depends(get_db)):
    invitation = db.query(FamilyInvitation).filter(
        FamilyInvitation.token == token, FamilyInvitation.status == "pending",
        FamilyInvitation.expires_at > datetime.utcnow(),
    ).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation is invalid or expired.")
    if payload.role != UserRole.parent.value or payload.email.lower() != invitation.invited_email:
        raise HTTPException(status_code=400, detail="Invitation details do not match.")
    if db.query(User).filter(User.email == invitation.invited_email).first():
        raise HTTPException(status_code=409, detail="This email is already registered.")
    if not payload.password:
        raise HTTPException(status_code=400, detail="A password is required to accept an invitation.")
    user = User(email=invitation.invited_email, full_name=payload.full_name.strip(), password_hash=get_password_hash(payload.password), role=UserRole.parent.value, is_active=True)
    db.add(user)
    db.flush()
    member = FamilyMember(family_id=invitation.family_id, user_id=user.id, role=UserRole.parent.value)
    db.add(member)
    invitation.status = "accepted"
    db.commit()
    db.refresh(member)
    return member


@router.patch("/members/{user_id}", response_model=FamilyMemberRead)
def update_member(user_id: str, payload: FamilyMemberUpdate, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    family = get_family_for_user(db, current_user.id)
    member = db.query(FamilyMember).filter(FamilyMember.family_id == family.id if family else "", FamilyMember.user_id == user_id).first() if family else None
    if not member or not member.user.is_active:
        raise HTTPException(status_code=404, detail="Family member not found.")
    if payload.full_name is not None:
        member.user.full_name = payload.full_name.strip()
    if payload.avatar is not None:
        member.user.avatar = payload.avatar.strip()
    db.commit()
    db.refresh(member)
    return member


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(user_id: str, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    family = get_family_for_user(db, current_user.id)
    member = db.query(FamilyMember).filter(FamilyMember.family_id == family.id if family else "", FamilyMember.user_id == user_id).first() if family else None
    if not member or not member.user.is_active:
        raise HTTPException(status_code=404, detail="Family member not found.")
    if member.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot remove yourself from the family.")
    if member.role == UserRole.parent.value and db.query(FamilyMember).filter(
        FamilyMember.family_id == family.id, FamilyMember.role == UserRole.parent.value
    ).count() <= 1:
        raise HTTPException(status_code=400, detail="The family must have at least one parent.")
    member.user.is_active = False
    db.delete(member)
    db.commit()
