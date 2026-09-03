"""FamilyQuest domain API.

All resources are scoped to the authenticated user's family.  Parent-only
operations are protected both by the dependency and by membership checks.
"""

from datetime import date, datetime, timedelta
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_user_family, require_parent
from app.core.security import get_password_hash
from app.database import get_db
from app.models.familyquest import (
    Achievement,
    AdventurePoint,
    AdventurePointClaim,
    CompletionStatus,
    DailyStreak,
    Family,
    FamilyMember,
    Notification,
    Reward,
    RewardRedemption,
    RewardRedemptionStatus,
    Task,
    TaskAssignment,
    TaskCompletion,
    TaskRating,
    User,
    UserAchievement,
    UserRole,
    UserStat,
    XPTransaction,
)
from app.push import queue_notification_push
from app.schemas.quest import (
    AchievementCreate,
    AchievementRead,
    AchievementUpdate,
    AdventurePointCreate,
    AdventurePointRead,
    AdventurePointUpdate,
    AdventureReorder,
    AssignmentCreate,
    AssignmentRead,
    ChildCreate,
    CompletionCreate,
    CompletionRead,
    CompletionReview,
    NotificationRead,
    RatingCreate,
    RedemptionRead,
    RedemptionReview,
    RewardCreate,
    RewardRead,
    StatsRead,
    TaskCreate,
    TaskRead,
    TaskUpdate,
)
from app.schemas.auth import UserRead

router = APIRouter()


def family_or_404(db: Session, user: User) -> Family:
    family = get_user_family(db, user.id)
    if not family:
        raise HTTPException(status_code=404, detail="You do not belong to a family.")
    return family


def member_or_404(db: Session, family_id: str, user_id: str) -> User:
    member = (
        db.query(FamilyMember)
        .filter(FamilyMember.family_id == family_id, FamilyMember.user_id == user_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="User is not a member of this family.")
    return member.user


def child_ids(db: Session, family_id: str, ids: list[str]) -> list[str]:
    unique_ids = list(dict.fromkeys(ids))
    if not unique_ids:
        return []
    members = (
        db.query(FamilyMember)
        .join(User)
        .filter(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id.in_(unique_ids),
            FamilyMember.role == UserRole.child.value,
            User.is_active.is_(True),
        )
        .all()
    )
    found = {member.user_id for member in members}
    if found != set(unique_ids):
        raise HTTPException(status_code=400, detail="Tasks may only be assigned to active children in your family.")
    return unique_ids


def notify(db: Session, user_id: str, kind: str, title: str, message: str) -> None:
    db.add(Notification(user_id=user_id, type=kind, title=title, message=message))
    queue_notification_push(db, user_id, title, message)


def get_task(db: Session, family_id: str, task_id: str) -> Task:
    task = (
        db.query(Task)
        .options(joinedload(Task.assignments), joinedload(Task.completions))
        .filter(Task.id == task_id, Task.family_id == family_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


def refresh_progress(db: Session, user_id: str, family_id: str) -> None:
    completed = (
        db.query(TaskCompletion)
        .join(Task)
        .filter(
            Task.family_id == family_id,
            TaskCompletion.user_id == user_id,
            TaskCompletion.status == CompletionStatus.approved.value,
        )
        .count()
    )
    total_xp = (
        db.query(func.coalesce(func.sum(XPTransaction.amount), 0))
        .filter(XPTransaction.user_id == user_id)
        .scalar()
        or 0
    )
    ratings = (
        db.query(func.avg(TaskRating.value))
        .join(TaskCompletion)
        .join(Task)
        .filter(Task.family_id == family_id, TaskCompletion.user_id == user_id)
        .scalar()
    )
    achievements = (
        db.query(UserAchievement)
        .join(Achievement)
        .filter(
            UserAchievement.user_id == user_id,
            Achievement.family_id == family_id,
            UserAchievement.is_unlocked.is_(True),
        )
        .count()
    )
    stat = db.query(UserStat).filter(UserStat.user_id == user_id).first()
    if not stat:
        stat = UserStat(user_id=user_id)
        db.add(stat)
    stat.total_tasks_completed = completed
    stat.total_xp = max(0, int(total_xp))
    stat.average_rating = round(float(ratings or 0))
    stat.achievements_count = achievements


def update_streak(db: Session, user_id: str) -> None:
    today = date.today()
    streak = db.query(DailyStreak).filter(DailyStreak.user_id == user_id).first()
    if not streak:
        streak = DailyStreak(user_id=user_id, current_streak=1, longest_streak=1, last_completed_date=today.isoformat())
        db.add(streak)
        return
    if streak.last_completed_date == today.isoformat():
        return
    previous = None
    if streak.last_completed_date:
        try:
            previous = date.fromisoformat(streak.last_completed_date)
        except ValueError:
            previous = None
    streak.current_streak = (streak.current_streak + 1) if previous == today - timedelta(days=1) else 1
    streak.longest_streak = max(streak.longest_streak, streak.current_streak)
    streak.last_completed_date = today.isoformat()


def unlock_achievements(db: Session, user: User, family_id: str) -> None:
    completed = (
        db.query(TaskCompletion)
        .join(Task)
        .filter(Task.family_id == family_id, TaskCompletion.user_id == user.id, TaskCompletion.status == "approved")
        .count()
    )
    xp = db.query(func.coalesce(func.sum(XPTransaction.amount), 0)).filter(XPTransaction.user_id == user.id).scalar() or 0
    for achievement in db.query(Achievement).filter(Achievement.family_id == family_id).all():
        record = (
            db.query(UserAchievement)
            .filter(UserAchievement.user_id == user.id, UserAchievement.achievement_id == achievement.id)
            .first()
        )
        if not record:
            record = UserAchievement(user_id=user.id, achievement_id=achievement.id)
            db.add(record)
            db.flush()
        requirement = achievement.requirement.lower()
        match = re.search(r"(\d+)", requirement)
        target = int(match.group(1)) if match else 1
        progress = int(xp if "xp" in requirement else completed)
        record.progress = progress
        if not record.is_unlocked and progress >= target:
            record.is_unlocked = True
            record.unlocked_at = datetime.utcnow()
            if achievement.xp_reward:
                db.add(XPTransaction(user_id=user.id, amount=achievement.xp_reward, reason=f"Achievement: {achievement.name}"))
            notify(db, user.id, "achievement", "Odemčený achievement", achievement.name)


def stats_for(db: Session, user: User, family_id: str) -> StatsRead:
    refresh_progress(db, user.id, family_id)
    db.flush()
    stat = db.query(UserStat).filter(UserStat.user_id == user.id).first()
    streak = db.query(DailyStreak).filter(DailyStreak.user_id == user.id).first()
    pending = (
        db.query(TaskCompletion)
        .join(Task)
        .filter(Task.family_id == family_id, TaskCompletion.user_id == user.id, TaskCompletion.status == "pending")
        .count()
    )
    total_xp = stat.total_xp if stat else 0
    level = total_xp // 100 + 1
    return StatsRead(
        user_id=user.id,
        total_tasks_completed=stat.total_tasks_completed if stat else 0,
        total_xp=total_xp,
        level=level,
        xp_in_level=total_xp % 100,
        xp_for_next_level=100,
        average_rating=float(stat.average_rating if stat else 0),
        achievements_count=stat.achievements_count if stat else 0,
        current_streak=streak.current_streak if streak else 0,
        longest_streak=streak.longest_streak if streak else 0,
        pending_completions=pending,
    )


def adventure_status(point: AdventurePoint, total_xp: int, level: int, current_seen: bool) -> tuple[str, bool]:
    """Return a display status without persisting progress or duplicating XP."""
    meets_requirements = total_xp >= point.required_xp and (
        point.required_level is None or level >= point.required_level
    )
    if meets_requirements:
        return "completed", current_seen
    if not current_seen:
        return "current", True
    return "locked", current_seen


def adventure_read(
    db: Session,
    family_id: str,
    user_id: str,
    child_id: str | None = None,
    include_inactive: bool = False,
) -> list[AdventurePointRead]:
    target_id = child_id or user_id
    if child_id:
        member = db.query(FamilyMember).filter(
            FamilyMember.family_id == family_id,
            FamilyMember.user_id == child_id,
            FamilyMember.role == UserRole.child.value,
        ).first()
        if not member:
            raise HTTPException(status_code=404, detail="Child not found in this family.")
    xp = max(0, int(
        db.query(func.coalesce(func.sum(XPTransaction.amount), 0))
        .filter(XPTransaction.user_id == target_id)
        .scalar() or 0
    ))
    level = xp // 100 + 1
    query = db.query(AdventurePoint).filter(AdventurePoint.family_id == family_id)
    if not query.first():
        defaults = [
            ("Zahájení cesty", "Vydej se na svou první výpravu.", "🏠", 14, 82, 0, 0, 50),
            ("První krůčky", "Každý splněný úkol tě posune dál.", "🌱", 28, 68, 50, 50, 75),
            ("Tajná jeskyně", "Objev skryté místo na své mapě.", "🪨", 20, 48, 100, 100, 100),
            ("Lesní průsmyk", "Projdi kouzelným lesem.", "🌲", 44, 55, 250, 250, 125),
            ("Vodopád odvahy", "Překonej další velkou výzvu.", "💧", 64, 38, 500, 500, 150),
            ("Strážce hor", "Jsi blízko vrcholu své cesty.", "🏔️", 49, 22, 750, 750, 200),
            ("Rodinný hrad", "Cílový bod společné výpravy.", "🏰", 80, 14, 1000, 1000, 250),
        ]
        db.add_all([
            AdventurePoint(
                family_id=family_id,
                title=title,
                description=description,
                icon=icon,
                position_x=position_x,
                position_y=position_y,
                order_index=order_index,
                required_xp=required_xp,
                reward_xp=reward_xp,
            )
            for title, description, icon, position_x, position_y, order_index, required_xp, reward_xp in defaults
        ])
        db.commit()
        query = db.query(AdventurePoint).filter(AdventurePoint.family_id == family_id)
    if not include_inactive:
        query = query.filter(AdventurePoint.is_active.is_(True))
    points = query.order_by(AdventurePoint.order_index, AdventurePoint.created_at).all()
    current_seen = False
    result = []
    for point in points:
        point_status, current_seen = adventure_status(point, xp, level, current_seen)
        result.append(AdventurePointRead.model_validate(point).model_copy(update={"status": point_status}))
    target_member = db.query(FamilyMember).filter(
        FamilyMember.family_id == family_id,
        FamilyMember.user_id == target_id,
        FamilyMember.role == UserRole.child.value,
    ).first()
    if target_member and not child_id:
        current_user_id = target_id
        newly_claimed = [
            point for point, item in zip(points, result)
            if item.status == "completed"
            and point.reward_xp
            and not db.query(AdventurePointClaim).filter_by(point_id=point.id, user_id=current_user_id).first()
        ]
        if newly_claimed:
            for point in newly_claimed:
                db.add(AdventurePointClaim(point_id=point.id, user_id=current_user_id))
                db.add(XPTransaction(user_id=current_user_id, amount=point.reward_xp, reason=f"Milník: {point.title}"))
            db.commit()
    return result


@router.get("/adventure", response_model=list[AdventurePointRead])
@router.get("/adventures", response_model=list[AdventurePointRead], include_in_schema=False)
@router.get("/adventure/points", response_model=list[AdventurePointRead], include_in_schema=False)
@router.get("/adventure/progress", response_model=list[AdventurePointRead], include_in_schema=False)
def list_adventure_points(
    child_id: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    family = family_or_404(db, current_user)
    if child_id and current_user.role != UserRole.parent.value:
        raise HTTPException(status_code=403, detail="Only parents can view another child's adventure.")
    return adventure_read(
        db,
        family.id,
        current_user.id,
        child_id,
        include_inactive=current_user.role == UserRole.parent.value,
    )


@router.post("/adventure/points/{point_id}/claim")
def claim_adventure_point(
    point_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    family = family_or_404(db, current_user)
    point = db.query(AdventurePoint).filter(
        AdventurePoint.id == point_id,
        AdventurePoint.family_id == family.id,
        AdventurePoint.is_active.is_(True),
    ).first()
    if not point:
        raise HTTPException(status_code=404, detail="Milník nebyl nalezen.")
    if current_user.role != UserRole.child.value:
        raise HTTPException(status_code=403, detail="Odměny za milníky může vyzvedávat pouze dítě.")
    xp = int(db.query(func.coalesce(func.sum(XPTransaction.amount), 0)).filter(XPTransaction.user_id == current_user.id).scalar() or 0)
    level = xp // 100 + 1
    if not adventure_status(point, xp, level, True)[0] == "completed":
        raise HTTPException(status_code=409, detail="Tento milník ještě není dokončený.")
    if db.query(AdventurePointClaim).filter_by(point_id=point.id, user_id=current_user.id).first():
        return {"awarded_xp": 0, "message": "Odměna za tento milník již byla vyzvednuta."}
    db.add(AdventurePointClaim(point_id=point.id, user_id=current_user.id))
    if point.reward_xp:
        db.add(XPTransaction(user_id=current_user.id, amount=point.reward_xp, reason=f"Milník: {point.title}"))
    db.commit()
    return {"awarded_xp": point.reward_xp, "message": f"Získali jste +{point.reward_xp} XP za milník {point.title}."}


@router.post("/adventure/points", response_model=AdventurePointRead, status_code=status.HTTP_201_CREATED)
@router.post("/adventure-points", response_model=AdventurePointRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/adventures", response_model=AdventurePointRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/adventure", response_model=AdventurePointRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_adventure_point(
    payload: AdventurePointCreate,
    current_user: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    family = family_or_404(db, current_user)
    values = payload.model_dump(exclude={"name", "order", "order_index"}, exclude_none=True)
    values["order_index"] = payload.order_index
    if values["order_index"] is None:
        values["order_index"] = (db.query(func.coalesce(func.max(AdventurePoint.order_index), -1))
                                  .filter(AdventurePoint.family_id == family.id).scalar() or -1) + 1
    point = AdventurePoint(family_id=family.id, **values)
    db.add(point)
    db.commit()
    db.refresh(point)
    return AdventurePointRead.model_validate(point).model_copy(update={"status": "locked"})


@router.patch("/adventure/points/{point_id}", response_model=AdventurePointRead)
@router.patch("/adventure-points/{point_id}", response_model=AdventurePointRead, include_in_schema=False)
@router.patch("/adventures/{point_id}", response_model=AdventurePointRead, include_in_schema=False)
@router.patch("/adventure/{point_id}", response_model=AdventurePointRead, include_in_schema=False)
@router.put("/adventure/points/{point_id}", response_model=AdventurePointRead, include_in_schema=False)
def update_adventure_point(
    point_id: str,
    payload: AdventurePointUpdate,
    current_user: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    family = family_or_404(db, current_user)
    point = db.query(AdventurePoint).filter(
        AdventurePoint.id == point_id, AdventurePoint.family_id == family.id
    ).first()
    if not point:
        raise HTTPException(status_code=404, detail="Adventure point not found.")
    values = payload.model_dump(exclude={"name", "order"}, exclude_unset=True)
    for field, value in values.items():
        setattr(point, field, value)
    db.commit()
    db.refresh(point)
    return AdventurePointRead.model_validate(point).model_copy(update={"status": "locked"})


@router.delete("/adventure/points/{point_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/adventure-points/{point_id}", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
@router.delete("/adventures/{point_id}", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
@router.delete("/adventure/{point_id}", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
def delete_adventure_point(
    point_id: str,
    current_user: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    family = family_or_404(db, current_user)
    point = db.query(AdventurePoint).filter(
        AdventurePoint.id == point_id, AdventurePoint.family_id == family.id
    ).first()
    if not point:
        raise HTTPException(status_code=404, detail="Adventure point not found.")
    db.delete(point)
    db.commit()


@router.post("/adventure/reorder", response_model=list[AdventurePointRead])
@router.post("/adventure/points/reorder", response_model=list[AdventurePointRead], include_in_schema=False)
def reorder_adventure_points(
    payload: AdventureReorder,
    current_user: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    family = family_or_404(db, current_user)
    if len(set(payload.point_ids)) != len(payload.point_ids):
        raise HTTPException(status_code=400, detail="Each adventure point may appear only once.")
    points = db.query(AdventurePoint).filter(
        AdventurePoint.family_id == family.id,
        AdventurePoint.id.in_(payload.point_ids),
    ).all()
    by_id = {point.id: point for point in points}
    if len(by_id) != len(points) or set(by_id) != set(payload.point_ids):
        raise HTTPException(status_code=400, detail="All points must belong to this family.")
    for index, point_id in enumerate(payload.point_ids):
        by_id[point_id].order_index = index
    db.commit()
    return adventure_read(db, family.id, current_user.id)


@router.post("/family/children", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@router.post("/children", response_model=UserRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_child(payload: ChildCreate, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    family = family_or_404(db, current_user)
    email = payload.email.lower() if payload.email else f"child-{uuid.uuid4().hex[:12]}@familyquest.app"
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="A user with this email already exists.")
    child = User(email=email, full_name=payload.full_name, password_hash=get_password_hash(payload.password), role="child", is_active=True)
    db.add(child)
    db.flush()
    db.add(FamilyMember(family_id=family.id, user_id=child.id, role="child"))
    db.commit()
    db.refresh(child)
    return child


@router.delete("/family/children/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/children/{user_id}", status_code=status.HTTP_204_NO_CONTENT, include_in_schema=False)
def remove_child(user_id: str, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    family = family_or_404(db, current_user)
    member = db.query(FamilyMember).filter(FamilyMember.family_id == family.id, FamilyMember.user_id == user_id, FamilyMember.role == "child").first()
    if not member:
        raise HTTPException(status_code=404, detail="Child not found.")
    member.user.is_active = False
    db.commit()


@router.get("/tasks", response_model=list[TaskRead])
def list_tasks(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    family = family_or_404(db, current_user)
    query = db.query(Task).options(joinedload(Task.assignments), joinedload(Task.completions)).filter(Task.family_id == family.id, Task.is_active.is_(True))
    if current_user.role == "child":
        query = query.join(TaskAssignment).filter(TaskAssignment.user_id == current_user.id)
    return query.order_by(Task.due_date.asc(), Task.created_at.desc()).all()


@router.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    family = family_or_404(db, current_user)
    task = Task(
        family_id=family.id, title=payload.title, description=payload.description, category=payload.category,
        difficulty=payload.difficulty, xp=payload.xp if payload.xp is not None else payload.difficulty * 10,
        repeat_mode=payload.repeat_mode, due_time=payload.due_time, due_date=payload.due_date, created_by=current_user.id,
    )
    db.add(task)
    db.flush()
    for user_id in child_ids(db, family.id, payload.assignee_ids):
        db.add(TaskAssignment(task_id=task.id, user_id=user_id))
        notify(db, user_id, "task", "Nový úkol", f"Byl vám přidělen úkol „{task.title}“.")
    db.commit()
    return get_task(db, family.id, task.id)


@router.get("/tasks/{task_id}", response_model=TaskRead)
def read_task(task_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = get_task(db, family_or_404(db, current_user).id, task_id)
    if current_user.role == "child" and not any(a.user_id == current_user.id for a in task.assignments):
        raise HTTPException(status_code=403, detail="This task is not assigned to you.")
    return task


@router.patch("/tasks/{task_id}", response_model=TaskRead)
@router.put("/tasks/{task_id}", response_model=TaskRead, include_in_schema=False)
def update_task(task_id: str, payload: TaskUpdate, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    family = family_or_404(db, current_user)
    task = get_task(db, family.id, task_id)
    values = payload.model_dump(exclude_unset=True)
    if values.get("category") is None:
        values["category"] = "home"
    assignees = values.pop("assignee_ids", None)
    for key, value in values.items():
        setattr(task, key, value)
    if assignees is not None:
        child_ids(db, family.id, assignees)
        task.assignments.clear()
        for user_id in assignees:
            task.assignments.append(TaskAssignment(user_id=user_id))
            notify(db, user_id, "task", "Úkol byl upraven", f"Úkol „{task.title}“ byl aktualizován.")
    else:
        for assignment in task.assignments:
            notify(db, assignment.user_id, "task", "Úkol byl upraven", f"Úkol „{task.title}“ byl aktualizován.")
    db.commit()
    return get_task(db, family.id, task.id)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_task(task_id: str, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    task = get_task(db, family_or_404(db, current_user).id, task_id)
    for assignment in task.assignments:
        notify(db, assignment.user_id, "task", "Úkol byl zrušen", f"Úkol „{task.title}“ byl zrušen.")
    task.is_active = False
    db.commit()


@router.post("/tasks/{task_id}/assign", response_model=list[AssignmentRead])
def assign_task(task_id: str, payload: AssignmentCreate, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    family = family_or_404(db, current_user)
    task = get_task(db, family.id, task_id)
    ids = child_ids(db, family.id, payload.user_ids)
    for user_id in ids:
        if not db.query(TaskAssignment).filter(TaskAssignment.task_id == task.id, TaskAssignment.user_id == user_id).first():
            db.add(TaskAssignment(task_id=task.id, user_id=user_id))
            notify(db, user_id, "task", "Nový úkol", f"Byl vám přidělen úkol „{task.title}“.")
    db.commit()
    return db.query(TaskAssignment).filter(TaskAssignment.task_id == task.id).all()


@router.delete("/tasks/{task_id}/assign/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_task(task_id: str, user_id: str, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    family = family_or_404(db, current_user)
    task = get_task(db, family.id, task_id)
    assignment = db.query(TaskAssignment).filter(TaskAssignment.task_id == task.id, TaskAssignment.user_id == user_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    db.delete(assignment)
    db.commit()


@router.get("/completions", response_model=list[CompletionRead])
def list_completions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    family = family_or_404(db, current_user)
    query = db.query(TaskCompletion).join(Task).filter(Task.family_id == family.id)
    if current_user.role == "child":
        query = query.filter(TaskCompletion.user_id == current_user.id)
    return query.order_by(TaskCompletion.completed_at.desc()).all()


@router.post("/tasks/{task_id}/complete", response_model=CompletionRead, status_code=status.HTTP_201_CREATED)
@router.post("/tasks/{task_id}/completion", response_model=CompletionRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def complete_task(task_id: str, payload: CompletionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    family = family_or_404(db, current_user)
    task = get_task(db, family.id, task_id)
    if current_user.role == "child" and not db.query(TaskAssignment).filter(TaskAssignment.task_id == task.id, TaskAssignment.user_id == current_user.id).first():
        raise HTTPException(status_code=403, detail="Můžete potvrdit pouze úkoly, které vám byly přiděleny.")
    existing = db.query(TaskCompletion).filter(TaskCompletion.task_id == task.id, TaskCompletion.user_id == current_user.id, TaskCompletion.status == "pending").first()
    if existing:
        raise HTTPException(status_code=409, detail="Tento úkol již čeká na schválení rodičem.")
    completion = TaskCompletion(task_id=task.id, user_id=current_user.id, notes=payload.notes, status="approved" if current_user.role == "parent" else "pending")
    db.add(completion)
    db.flush()
    if completion.status == "approved":
        db.add(XPTransaction(user_id=current_user.id, amount=task.xp, reason=f"Completed: {task.title}"))
        update_streak(db, current_user.id)
        unlock_achievements(db, current_user, family.id)
    else:
        for member in db.query(FamilyMember).filter(FamilyMember.family_id == family.id, FamilyMember.role == "parent").all():
            if member.user_id != current_user.id:
                notify(db, member.user_id, "completion", "Úkol čeká na schválení", f"{current_user.full_name} dokončil(a) úkol {task.title}.")
    db.commit()
    db.refresh(completion)
    return completion


@router.post("/completions/{completion_id}/review", response_model=CompletionRead)
@router.patch("/completions/{completion_id}", response_model=CompletionRead, include_in_schema=False)
def review_completion(completion_id: str, payload: CompletionReview, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    family = family_or_404(db, current_user)
    completion = db.query(TaskCompletion).join(Task).filter(TaskCompletion.id == completion_id, Task.family_id == family.id).first()
    if not completion:
        raise HTTPException(status_code=404, detail="Dokončení úkolu nebylo nalezeno.")
    if completion.status != "pending":
        raise HTTPException(status_code=409, detail="Toto dokončení úkolu již bylo vyhodnoceno.")
    completion.status = payload.status
    completion.reviewed_at = datetime.utcnow()
    if payload.notes is not None:
        completion.notes = payload.notes
    if payload.status == "approved":
        db.add(XPTransaction(user_id=completion.user_id, amount=completion.task.xp, reason=f"Completed: {completion.task.title}"))
        update_streak(db, completion.user_id)
        unlock_achievements(db, completion.user, family.id)
        notify(db, completion.user_id, "completion", "Úkol schválen", f"Za úkol {completion.task.title} jste získali {completion.task.xp} XP.")
    else:
        reason = payload.notes.strip() if payload.notes and payload.notes.strip() else "Zkontroluj prosím úkol a zkus ho znovu."
        notify(db, completion.user_id, "completion", "Úkol je potřeba přepracovat", f"{completion.task.title}: {reason}")
    db.commit()
    db.refresh(completion)
    return completion


@router.post("/completions/{completion_id}/rate", response_model=CompletionRead)
@router.post("/completions/{completion_id}/rating", response_model=CompletionRead, include_in_schema=False)
def rate_completion(completion_id: str, payload: RatingCreate, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    family = family_or_404(db, current_user)
    completion = db.query(TaskCompletion).join(Task).filter(TaskCompletion.id == completion_id, Task.family_id == family.id).first()
    if not completion or completion.status != "approved":
        raise HTTPException(status_code=404, detail="An approved completion is required before rating.")
    if db.query(TaskRating).filter(TaskRating.completion_id == completion.id).first():
        raise HTTPException(status_code=409, detail="This completion has already been rated.")
    db.add(TaskRating(completion_id=completion.id, rated_by_user_id=current_user.id, value=payload.value, comment=payload.comment))
    db.commit()
    return completion


@router.get("/stats", response_model=StatsRead)
@router.get("/statistics", response_model=StatsRead, include_in_schema=False)
def my_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return stats_for(db, current_user, family_or_404(db, current_user).id)


@router.get("/users/{user_id}/stats", response_model=StatsRead)
def user_stats(user_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    family = family_or_404(db, current_user)
    user = member_or_404(db, family.id, user_id)
    if current_user.role == "child" and user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Children can only view their own statistics.")
    return stats_for(db, user, family.id)


@router.get("/leaderboard", response_model=list[StatsRead])
def leaderboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    family = family_or_404(db, current_user)
    members = db.query(FamilyMember).filter(FamilyMember.family_id == family.id, FamilyMember.role == "child").all()
    results = [stats_for(db, member.user, family.id) for member in members]
    return sorted(results, key=lambda item: item.total_xp, reverse=True)


@router.get("/achievements", response_model=list[AchievementRead])
def list_achievements(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    family = family_or_404(db, current_user)
    achievements = db.query(Achievement).filter(Achievement.family_id == family.id).all()
    records = {record.achievement_id: record for record in db.query(UserAchievement).filter(UserAchievement.user_id == current_user.id).all()}
    return [
        AchievementRead.model_validate(achievement).model_copy(update={
            "progress": records.get(achievement.id).progress if records.get(achievement.id) else 0,
            "is_unlocked": records.get(achievement.id).is_unlocked if records.get(achievement.id) else False,
            "unlocked_at": records.get(achievement.id).unlocked_at if records.get(achievement.id) else None,
        })
        for achievement in achievements
    ]


@router.post("/achievements", response_model=AchievementRead, status_code=status.HTTP_201_CREATED)
def create_achievement(payload: AchievementCreate, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    family = family_or_404(db, current_user)
    achievement = Achievement(family_id=family.id, **payload.model_dump())
    db.add(achievement)
    db.commit()
    db.refresh(achievement)
    return achievement


@router.patch("/achievements/{achievement_id}", response_model=AchievementRead)
def update_achievement(
    achievement_id: str,
    payload: AchievementUpdate,
    current_user: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    family = family_or_404(db, current_user)
    achievement = db.query(Achievement).filter(
        Achievement.id == achievement_id,
        Achievement.family_id == family.id,
    ).first()
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(achievement, field, value)
    db.add(achievement)
    db.commit()
    db.refresh(achievement)
    return achievement


@router.delete("/achievements/{achievement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_achievement(
    achievement_id: str,
    current_user: User = Depends(require_parent),
    db: Session = Depends(get_db),
):
    family = family_or_404(db, current_user)
    achievement = db.query(Achievement).filter(
        Achievement.id == achievement_id,
        Achievement.family_id == family.id,
    ).first()
    if not achievement:
        raise HTTPException(status_code=404, detail="Achievement not found.")
    db.delete(achievement)
    db.commit()


@router.get("/rewards", response_model=list[RewardRead])
def list_rewards(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Reward).filter(Reward.family_id == family_or_404(db, current_user).id, Reward.is_active.is_(True)).order_by(Reward.cost).all()


@router.post("/rewards", response_model=RewardRead, status_code=status.HTTP_201_CREATED)
def create_reward(payload: RewardCreate, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    reward = Reward(family_id=family_or_404(db, current_user).id, **payload.model_dump())
    db.add(reward)
    db.commit()
    db.refresh(reward)
    return reward


@router.patch("/rewards/{reward_id}", response_model=RewardRead)
def update_reward(reward_id: str, payload: RewardCreate, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    reward = db.query(Reward).filter(Reward.id == reward_id, Reward.family_id == family_or_404(db, current_user).id).first()
    if not reward:
        raise HTTPException(status_code=404, detail="Reward not found.")
    for key, value in payload.model_dump().items():
        setattr(reward, key, value)
    db.commit()
    return reward


@router.post("/rewards/{reward_id}/redeem", response_model=RedemptionRead, status_code=status.HTTP_201_CREATED)
def redeem_reward(reward_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    family = family_or_404(db, current_user)
    reward = db.query(Reward).filter(Reward.id == reward_id, Reward.family_id == family.id, Reward.is_active.is_(True)).first()
    if not reward:
        raise HTTPException(status_code=404, detail="Reward not found.")
    stats = stats_for(db, current_user, family.id)
    reserved = (
        db.query(func.coalesce(func.sum(Reward.cost), 0))
        .join(RewardRedemption, RewardRedemption.reward_id == Reward.id)
        .filter(
            RewardRedemption.user_id == current_user.id,
            RewardRedemption.status == RewardRedemptionStatus.pending.value,
            Reward.family_id == family.id,
        )
        .scalar()
        or 0
    )
    if stats.total_xp - int(reserved) < reward.cost:
        raise HTTPException(status_code=400, detail="Not enough XP for this reward.")
    pending = db.query(RewardRedemption).filter(RewardRedemption.reward_id == reward.id, RewardRedemption.user_id == current_user.id, RewardRedemption.status == "pending").first()
    if pending:
        raise HTTPException(status_code=409, detail="This reward is already awaiting review.")
    redemption = RewardRedemption(reward_id=reward.id, user_id=current_user.id)
    db.add(redemption)
    db.flush()
    for member in db.query(FamilyMember).filter(FamilyMember.family_id == family.id, FamilyMember.role == "parent").all():
        notify(db, member.user_id, "reward", "Nová žádost o odměnu", f"{current_user.full_name} požádal(a) o odměnu „{reward.name}“.")
    db.commit()
    db.refresh(redemption)
    return redemption


@router.get("/redemptions", response_model=list[RedemptionRead])
@router.get("/reward-redemptions", response_model=list[RedemptionRead], include_in_schema=False)
def list_redemptions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    family = family_or_404(db, current_user)
    query = db.query(RewardRedemption).join(Reward).filter(Reward.family_id == family.id)
    if current_user.role == "child":
        query = query.filter(RewardRedemption.user_id == current_user.id)
    return query.order_by(RewardRedemption.requested_at.desc()).all()


@router.post("/redemptions/{redemption_id}/review", response_model=RedemptionRead)
def review_redemption(redemption_id: str, payload: RedemptionReview, current_user: User = Depends(require_parent), db: Session = Depends(get_db)):
    family = family_or_404(db, current_user)
    redemption = db.query(RewardRedemption).join(Reward).filter(RewardRedemption.id == redemption_id, Reward.family_id == family.id).first()
    if not redemption:
        raise HTTPException(status_code=404, detail="Redemption not found.")
    if redemption.status != "pending":
        raise HTTPException(status_code=409, detail="This redemption has already been reviewed.")
    if payload.status == "approved":
        stats = stats_for(db, redemption.user, family.id)
        if stats.total_xp < redemption.reward.cost:
            raise HTTPException(status_code=400, detail="The child no longer has enough XP.")
        db.add(XPTransaction(user_id=redemption.user_id, amount=-redemption.reward.cost, reason=f"Reward: {redemption.reward.name}"))
    redemption.status = payload.status
    redemption.reviewed_at = datetime.utcnow()
    notify(db, redemption.user_id, "reward", "Odměna schválena" if payload.status == "approved" else "Odměna zamítnuta", f"Žádost o odměnu „{redemption.reward.name}“ byla vyřízena.")
    db.commit()
    db.refresh(redemption)
    return redemption


@router.get("/notifications", response_model=list[NotificationRead])
def list_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).limit(100).all()


@router.post("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_notification_read(notification_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == current_user.id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found.")
    db.delete(notification)
    db.commit()
    return None


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_notifications_read(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.user_id == current_user.id).delete(synchronize_session=False)
    db.commit()
