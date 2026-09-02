from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models.familyquest import Family, FamilyMember, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_user_with_impersonation(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> tuple[User, User | None, str | None]:
    """
    Returns (actual_user, impersonated_user, impersonated_by_user_id)
    If impersonated_by is present in token, user is impersonating someone else.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception

    impersonated_by = payload.get("impersonated_by")
    if impersonated_by:
        actual_user = db.query(User).filter(User.id == impersonated_by).first()
        if actual_user is None:
            raise credentials_exception
        return actual_user, user, impersonated_by
    
    return user, None, None


def require_parent(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "parent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only parents can access this endpoint.",
        )
    return current_user


def get_user_family(db: Session, user_id: str) -> Family | None:
    membership = (
        db.query(FamilyMember)
        .filter(FamilyMember.user_id == user_id)
        .first()
    )
    if not membership:
        return None
    return db.query(Family).filter(Family.id == membership.family_id).first()


def require_family(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> tuple[User, Family]:
    family = get_user_family(db, current_user.id)
    if not family:
        raise HTTPException(status_code=404, detail="You do not belong to a family.")
    return current_user, family
