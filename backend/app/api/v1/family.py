from datetime import datetime, timedelta
import smtplib
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_parent
from app.core.security import create_access_token, get_password_hash
from app.crud.family import create_family, get_family_for_user, list_family_members
from app.database import get_db
from app.models.familyquest import FamilyInvitation, FamilyMember, User, UserRole
from app.schemas.family import (
    FamilyCreate, FamilyInvitationCreate, FamilyInvitationRead, FamilyMemberCreate, FamilyMemberRead,
    FamilyMemberUpdate, FamilyAccountPasswordUpdate, FamilyAccountRoleUpdate,
    FamilyAccountStatusUpdate, FamilyRead, FamilyInvitationPublicRead, InvitationRegistration,
)
from app.services.email import send_family_invitation

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
    members = list_family_members(db, family.id, include_inactive=current_user.role == UserRole.parent.value)
    return members


@router.get("/accounts", response_model=list[FamilyMemberRead])
def list_accounts(current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    family = get_family_for_user(db, current_user.id)
    if not family:
        raise HTTPException(status_code=404, detail="Family not found.")
    return list_family_members(db, family.id, include_inactive=True)


@router.get("/accounts/{user_id}", response_model=FamilyMemberRead)
def get_account(user_id: str, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    return get_member(user_id, current_user, db)


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
    if payload.role == UserRole.parent.value and not payload.email:
        raise HTTPException(status_code=400, detail="An email is required for a parent account.")
    email = payload.email.strip().lower() if payload.email else f"child-{secrets.token_hex(6)}@familyquest.app"
    if payload.role == UserRole.parent.value and not payload.password:
        raise HTTPException(status_code=400, detail="A password is required for a parent account.")
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        if db.query(FamilyMember).filter(FamilyMember.family_id == family.id, FamilyMember.user_id == existing.id).first():
            raise HTTPException(status_code=409, detail="This user is already a family member.")
        raise HTTPException(status_code=409, detail="This email is already registered.")
    user = User(email=email, full_name=payload.full_name.strip(), password_hash=get_password_hash(payload.password or secrets.token_urlsafe(16)), role=payload.role, is_active=True)
    db.add(user)
    db.flush()
    member = FamilyMember(family_id=family.id, user_id=user.id, role=payload.role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.post("/accounts", response_model=FamilyMemberRead, status_code=status.HTTP_201_CREATED)
def add_account(payload: FamilyMemberCreate, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    return add_member(payload, current_user, db)


@router.get("/invitations", response_model=list[FamilyInvitationRead])
def list_invitations(current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    family = get_family_for_user(db, current_user.id)
    if not family:
        raise HTTPException(status_code=404, detail="Family not found.")
    now = datetime.utcnow()
    pending = db.query(FamilyInvitation).filter(
        FamilyInvitation.family_id == family.id,
        FamilyInvitation.status == "pending",
        FamilyInvitation.expires_at > now,
    ).all()
    return pending


@router.post("/invitations", response_model=FamilyInvitationRead, status_code=status.HTTP_201_CREATED)
def invite_member(payload: FamilyInvitationCreate, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    family = get_family_for_user(db, current_user.id)
    if not family:
        raise HTTPException(status_code=404, detail="Family not found.")
    email = str(payload.email).lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="This email is already registered.")
    if db.query(FamilyMember).join(User).filter(
        FamilyMember.family_id == family.id, User.email == email
    ).first():
        raise HTTPException(status_code=409, detail="This user is already a family member.")
    active_invitation = db.query(FamilyInvitation).filter(
        FamilyInvitation.family_id == family.id,
        FamilyInvitation.invited_email == email,
        FamilyInvitation.status == "pending",
        FamilyInvitation.expires_at > datetime.utcnow(),
    ).first()
    if active_invitation:
        raise HTTPException(status_code=409, detail="An active invitation already exists for this email.")
    invitation = FamilyInvitation(
        family_id=family.id, invited_email=email,
        invited_name=(payload.full_name or email.split("@")[0]).strip(),
        role=payload.role,
        token=secrets.token_urlsafe(32), status="pending", created_by=current_user.id,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    try:
        send_family_invitation(recipient=email, family_name=family.name, token=invitation.token)
    except (smtplib.SMTPException, OSError, RuntimeError) as exc:
        db.delete(invitation)
        db.commit()
        raise HTTPException(status_code=503, detail="Invitation email could not be sent.") from exc
    return invitation


@router.get("/invitations/{token}", response_model=FamilyInvitationPublicRead)
def read_invitation(token: str, db: Session = Depends(get_db)):
    invitation = db.query(FamilyInvitation).filter(
        FamilyInvitation.token == token, FamilyInvitation.status == "pending",
        FamilyInvitation.expires_at > datetime.utcnow(),
    ).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation is invalid or expired.")
    return FamilyInvitationPublicRead(
        family_name=invitation.family.name, invited_email=invitation.invited_email,
        role=invitation.role, expires_at=invitation.expires_at,
    )


@router.post("/invitations/{token}/accept", response_model=FamilyMemberRead, status_code=status.HTTP_201_CREATED)
def accept_invitation(token: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    invitation = db.query(FamilyInvitation).filter(
        FamilyInvitation.token == token, FamilyInvitation.status == "pending",
        FamilyInvitation.expires_at > datetime.utcnow(),
    ).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation is invalid or expired.")
    if current_user.email.lower() != invitation.invited_email.lower():
        raise HTTPException(status_code=403, detail="This invitation belongs to a different email address.")
    if db.query(FamilyMember).filter(
        FamilyMember.family_id == invitation.family_id, FamilyMember.user_id == current_user.id
    ).first():
        raise HTTPException(status_code=409, detail="You are already a member of this family.")
    member = FamilyMember(family_id=invitation.family_id, user_id=current_user.id, role=invitation.role)
    db.add(member)
    invitation.status = "accepted"
    db.commit()
    db.refresh(member)
    return member


@router.post("/invitations/{token}/register", response_model=dict[str, str], status_code=status.HTTP_201_CREATED)
def register_from_invitation(token: str, payload: InvitationRegistration, db: Session = Depends(get_db)):
    invitation = db.query(FamilyInvitation).filter(
        FamilyInvitation.token == token, FamilyInvitation.status == "pending",
        FamilyInvitation.expires_at > datetime.utcnow(),
    ).first()
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation is invalid or expired.")
    email = str(payload.email).lower()
    if email != invitation.invited_email.lower():
        raise HTTPException(status_code=400, detail="Invitation email does not match.")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="This email is already registered. Sign in to accept the invitation.")
    user = User(
        email=email, full_name=payload.full_name.strip(),
        password_hash=get_password_hash(payload.password), role=invitation.role, is_active=True,
    )
    db.add(user)
    db.flush()
    member = FamilyMember(family_id=invitation.family_id, user_id=user.id, role=invitation.role)
    db.add(member)
    invitation.status = "accepted"
    db.commit()
    return {
        "access_token": create_access_token(
            subject=user.email, extra_claims={"user_id": user.id, "role": user.role}
        ),
        "token_type": "bearer",
    }


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_invitation(invitation_id: str, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    family = get_family_for_user(db, current_user.id)
    invitation = db.query(FamilyInvitation).filter(
        FamilyInvitation.id == invitation_id, FamilyInvitation.family_id == family.id if family else ""
    ).first() if family else None
    if not invitation or invitation.status != "pending":
        raise HTTPException(status_code=404, detail="Pending invitation not found.")
    invitation.status = "cancelled"
    db.commit()


@router.post("/invitations/{invitation_id}/resend", response_model=FamilyInvitationRead)
def resend_invitation(invitation_id: str, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    family = get_family_for_user(db, current_user.id)
    invitation = db.query(FamilyInvitation).filter(
        FamilyInvitation.id == invitation_id, FamilyInvitation.family_id == family.id if family else ""
    ).first() if family else None
    if not invitation or invitation.status != "pending":
        raise HTTPException(status_code=404, detail="Pending invitation not found.")
    invitation.expires_at = datetime.utcnow() + timedelta(days=7)
    db.commit()
    try:
        send_family_invitation(recipient=invitation.invited_email, family_name=family.name, token=invitation.token)
    except (smtplib.SMTPException, OSError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="Invitation email could not be sent.") from exc
    db.refresh(invitation)
    return invitation


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


@router.patch("/accounts/{user_id}", response_model=FamilyMemberRead)
def update_account(user_id: str, payload: FamilyMemberUpdate, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    return update_member(user_id, payload, current_user, db)


@router.post("/accounts/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_account_password(
    user_id: str,
    payload: FamilyAccountPasswordUpdate,
    current_user: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    family = get_family_for_user(db, current_user.id)
    member = db.query(FamilyMember).filter(
        FamilyMember.family_id == family.id if family else "", FamilyMember.user_id == user_id
    ).first() if family else None
    if not member or not member.user.is_active:
        raise HTTPException(status_code=404, detail="Family member not found.")
    member.user.password_hash = get_password_hash(payload.password)
    db.commit()


@router.patch("/accounts/{user_id}/status", response_model=FamilyMemberRead)
def update_account_status(
    user_id: str,
    payload: FamilyAccountStatusUpdate,
    current_user: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    family = get_family_for_user(db, current_user.id)
    member = db.query(FamilyMember).filter(
        FamilyMember.family_id == family.id if family else "", FamilyMember.user_id == user_id
    ).first() if family else None
    if not member:
        raise HTTPException(status_code=404, detail="Family member not found.")
    if member.user_id == current_user.id and not payload.is_active:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")
    if member.role == UserRole.parent.value and not payload.is_active and db.query(FamilyMember).join(User).filter(
        FamilyMember.family_id == family.id, FamilyMember.role == UserRole.parent.value,
        User.is_active.is_(True),
    ).count() <= 1:
        raise HTTPException(status_code=400, detail="The family must have at least one active parent.")
    member.user.is_active = payload.is_active
    db.commit()
    db.refresh(member)
    return member


@router.patch("/accounts/{user_id}/role", response_model=FamilyMemberRead)
def update_account_role(
    user_id: str,
    payload: FamilyAccountRoleUpdate,
    current_user: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    family = get_family_for_user(db, current_user.id)
    member = db.query(FamilyMember).filter(
        FamilyMember.family_id == family.id if family else "", FamilyMember.user_id == user_id
    ).first() if family else None
    if not member or not member.user.is_active:
        raise HTTPException(status_code=404, detail="Family member not found.")
    if member.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot change your own role.")
    if member.role == UserRole.parent.value and payload.role == UserRole.child.value and db.query(FamilyMember).join(User).filter(
        FamilyMember.family_id == family.id, FamilyMember.role == UserRole.parent.value,
        User.is_active.is_(True),
    ).count() <= 1:
        raise HTTPException(status_code=400, detail="The family must have at least one active parent.")
    member.role = payload.role
    member.user.role = payload.role
    db.commit()
    db.refresh(member)
    return member


@router.get("/accounts/{user_id}/preview", response_model=FamilyMemberRead)
def preview_account(user_id: str, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    """Validate family scope for a read-only child preview without impersonating."""
    member = get_member(user_id, current_user, db)
    if member.role != UserRole.child.value:
        raise HTTPException(status_code=400, detail="Only child accounts can be previewed.")
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
