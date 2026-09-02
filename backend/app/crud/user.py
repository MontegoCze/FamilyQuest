from sqlalchemy.orm import Session

from app.models.familyquest import Family, FamilyMember, User, UserRole


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, *, email: str, password_hash: str, full_name: str, role: str = UserRole.parent.value):
    user = User(
        email=email,
        password_hash=password_hash,
        full_name=full_name,
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_family_for_parent(db: Session, parent_user_id: str, family_name: str):
    family = Family(name=family_name)
    db.add(family)
    db.commit()
    db.refresh(family)

    membership = FamilyMember(family_id=family.id, user_id=parent_user_id, role=UserRole.parent.value)
    db.add(membership)
    db.commit()
    return family


def get_user_family(db: Session, user_id: str):
    membership = db.query(FamilyMember).filter(FamilyMember.user_id == user_id).first()
    if not membership:
        return None
    return db.query(Family).filter(Family.id == membership.family_id).first()
