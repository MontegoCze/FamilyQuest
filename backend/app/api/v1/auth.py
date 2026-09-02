from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, get_password_hash, verify_password
from app.crud.user import create_user, get_user_by_email
from app.database import get_db
from app.models.familyquest import User, UserRole
from app.schemas.auth import Token, UserAvatarUpdate, UserLogin, UserRead, UserRegister

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
