from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_parent, get_current_user_with_impersonation
from app.core.security import create_access_token, get_password_hash, verify_password
from app.crud.user import create_user, get_user_by_email
from app.database import get_db
from app.models.familyquest import PushToken, User, UserRole, FamilyMember
from app.schemas.auth import PushTokenUpsert, Token, UserAvatarUpdate, UserLogin, UserRead, UserRegister, SwitchAccountResponse

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegister, db: Session = Depends(get_db)):
    if get_user_by_email(db, str(payload.email).lower()):
        raise HTTPException(status_code=400, detail="User with this email already exists.")

    user = create_user(
        db,
        email=str(payload.email).lower(),
        password_hash=get_password_hash(payload.password),
        full_name=payload.full_name,
        role=UserRole.parent.value,
    )
    return user


@router.post("/login", response_model=Token)
def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    user = get_user_by_email(db, payload.email)
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(subject=user.email, extra_claims={"user_id": user.id, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserRead)
def update_current_user(
    payload: UserAvatarUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.avatar = payload.avatar.strip()
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/push-token", status_code=status.HTTP_204_NO_CONTENT)
def register_push_token(
    payload: PushTokenUpsert,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    push_token = db.query(PushToken).filter(PushToken.token == payload.token).first()
    if push_token:
        push_token.user_id = current_user.id
        push_token.platform = payload.platform
    else:
        db.add(PushToken(user_id=current_user.id, token=payload.token, platform=payload.platform))
    db.commit()


@router.post("/switch/{user_id}", response_model=SwitchAccountResponse)
def switch_account(
    user_id: str,
    current_user: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    """
    Bezpečné přepnutí na jiný účet. Rodič se stává "impersonovaným" a dostane nový token.
    Backend pozná, že je to impersonace, a bude to hlídat.
    """
    # Ověř, že target uživatel existuje a je v rodině
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user or not target_user.is_active:
        raise HTTPException(status_code=404, detail="User not found or inactive.")
    
    # Ověř, že oba uživatelé jsou ve stejné rodině
    current_member = db.query(FamilyMember).filter(FamilyMember.user_id == current_user.id).first()
    target_member = db.query(FamilyMember).filter(FamilyMember.user_id == target_user.id).first()
    
    if not current_member or not target_member or current_member.family_id != target_member.family_id:
        raise HTTPException(status_code=403, detail="User is not in your family.")
    
    # Rodič může přepínat jen dítě, ne jiného rodiče
    if target_user.role == UserRole.parent.value:
        raise HTTPException(status_code=403, detail="You can only switch to child accounts.")
    
    # Vytvoř nový token s impersonation claimem
    token = create_access_token(
        subject=target_user.email,
        extra_claims={
            "user_id": target_user.id,
            "role": target_user.role,
            "impersonated_by": current_user.id,
        }
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "impersonated_user_id": target_user.id,
        "impersonated_user_name": target_user.full_name,
        "impersonated_by_user_id": current_user.id,
    }


@router.post("/return", response_model=Token)
def return_to_parent(
    db: Session = Depends(get_db),
    user_data: tuple[User, User | None, str | None] = Depends(get_current_user_with_impersonation),
):
    """
    Vrátí se zpět k rodiči. Funkce se volá s tokenem, který obsahuje impersonated_by claim.
    """
    actual_user, impersonated_user, impersonated_by_user_id = user_data
    
    if not impersonated_by_user_id or not impersonated_user:
        raise HTTPException(
            status_code=400,
            detail="You are not impersonating anyone. Use /auth/login to login as someone else."
        )
    
    # Vytvoř nový token pro původního rodiče
    parent = db.query(User).filter(User.id == impersonated_by_user_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent user not found.")
    
    token = create_access_token(
        subject=parent.email,
        extra_claims={"user_id": parent.id, "role": parent.role}
    )
    
    return {"access_token": token, "token_type": "bearer"}
