from sqlalchemy.orm import Session

from app.models.familyquest import Family, FamilyMember, User, UserRole


def create_family(db: Session, *, name: str, parent_user: User):
    family = Family(name=name)
    db.add(family)
    db.commit()
    db.refresh(family)

    membership = FamilyMember(family_id=family.id, user_id=parent_user.id, role=UserRole.parent.value)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return family


def get_family_for_user(db: Session, user_id: str):
    member = db.query(FamilyMember).filter(FamilyMember.user_id == user_id).first()
    if not member:
        return None
    return db.query(Family).filter(Family.id == member.family_id).first()


def list_family_members(db: Session, family_id: str, *, include_inactive: bool = False):
    query = db.query(FamilyMember).join(User).filter(FamilyMember.family_id == family_id)
    if not include_inactive:
        query = query.filter(User.is_active.is_(True))
    return query.all()
