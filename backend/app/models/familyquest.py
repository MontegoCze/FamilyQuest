import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(str, Enum):
    parent = "parent"
    child = "child"


class TaskRepeatMode(str, Enum):
    once = "once"
    daily = "daily"
    weekdays = "weekdays"
    weekends = "weekends"
    custom = "custom"


class CompletionStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class RewardRedemptionStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Family(Base):
    __tablename__ = "families"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    members = relationship("FamilyMember", back_populates="family", cascade="all, delete-orphan")
    rewards = relationship("Reward", back_populates="family", cascade="all, delete-orphan")
    achievements = relationship("Achievement", back_populates="family", cascade="all, delete-orphan")
    adventure_points = relationship("AdventurePoint", back_populates="family", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default=UserRole.parent.value, nullable=False)
    avatar = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    memberships = relationship("FamilyMember", back_populates="user", cascade="all, delete-orphan")
    completions = relationship("TaskCompletion", back_populates="user")
    ratings = relationship("TaskRating", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    reward_redemptions = relationship("RewardRedemption", back_populates="user")
    xp_transactions = relationship("XPTransaction", back_populates="user")
    user_achievements = relationship("UserAchievement", back_populates="user")
    push_tokens = relationship("PushToken", back_populates="user", cascade="all, delete-orphan")


class PushToken(Base):
    __tablename__ = "push_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(512), unique=True, nullable=False)
    platform = Column(String(20), nullable=False, default="android")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="push_tokens")


class FamilyMember(Base):
    __tablename__ = "family_members"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    family_id = Column(String(36), ForeignKey("families.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    role = Column(String(20), default=UserRole.child.value, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    family = relationship("Family", back_populates="members")
    user = relationship("User", back_populates="memberships")

    @property
    def full_name(self) -> str:
        return self.user.full_name

    @property
    def email(self) -> str:
        return self.user.email

    @property
    def avatar(self) -> str | None:
        return self.user.avatar

    @property
    def is_active(self) -> bool:
        return self.user.is_active

    __table_args__ = (UniqueConstraint("family_id", "user_id", name="uq_family_member"),)


class FamilyInvitation(Base):
    __tablename__ = "family_invitations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    family_id = Column(String(36), ForeignKey("families.id"), nullable=False)
    invited_email = Column(String(255), nullable=False, index=True)
    invited_name = Column(String(255), nullable=False)
    role = Column(String(20), default=UserRole.child.value, nullable=False)
    token = Column(String(128), unique=True, nullable=False, index=True)
    status = Column(String(20), default="pending", nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    family = relationship("Family")
    inviter = relationship("User")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    family_id = Column(String(36), ForeignKey("families.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(120), nullable=False, default="home", server_default="home")
    difficulty = Column(Integer, default=1, nullable=False)
    xp = Column(Integer, default=10, nullable=False)
    repeat_mode = Column(String(20), default=TaskRepeatMode.once.value, nullable=False)
    due_time = Column(String(20), nullable=True)
    due_date = Column(String(50), nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (CheckConstraint("category IN ('home', 'school')", name="ck_tasks_category"),)

    completions = relationship("TaskCompletion", back_populates="task")
    assignments = relationship("TaskAssignment", back_populates="task")


class TaskAssignment(Base):
    __tablename__ = "task_assignments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    task = relationship("Task", back_populates="assignments")
    user = relationship("User")

    @property
    def user_name(self) -> str:
        return self.user.full_name

    __table_args__ = (UniqueConstraint("task_id", "user_id", name="uq_task_assignment"),)


class TaskCompletion(Base):
    __tablename__ = "task_completions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default=CompletionStatus.pending.value, nullable=False)
    completed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    task = relationship("Task", back_populates="completions")
    user = relationship("User", back_populates="completions")
    rating = relationship("TaskRating", uselist=False, back_populates="completion")


class TaskRating(Base):
    __tablename__ = "task_ratings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    completion_id = Column(String(36), ForeignKey("task_completions.id"), nullable=False, unique=True)
    rated_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    value = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="ratings")
    completion = relationship("TaskCompletion", back_populates="rating")


class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    family_id = Column(String(36), ForeignKey("families.id"), nullable=False)
    name = Column(String(255), nullable=False)
    icon = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    requirement = Column(Text, nullable=False)
    xp_reward = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user_achievements = relationship("UserAchievement", back_populates="achievement")
    family = relationship("Family", back_populates="achievements")


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    achievement_id = Column(String(36), ForeignKey("achievements.id"), nullable=False)
    unlocked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    progress = Column(Integer, default=0, nullable=False)
    is_unlocked = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="user_achievements")
    achievement = relationship("Achievement", back_populates="user_achievements")

    __table_args__ = (UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),)


class Reward(Base):
    __tablename__ = "rewards"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    family_id = Column(String(36), ForeignKey("families.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    cost = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    family = relationship("Family", back_populates="rewards")
    redemptions = relationship("RewardRedemption", back_populates="reward")


class RewardRedemption(Base):
    __tablename__ = "reward_redemptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    reward_id = Column(String(36), ForeignKey("rewards.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default=RewardRedemptionStatus.pending.value, nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="reward_redemptions")
    reward = relationship("Reward", back_populates="redemptions")

    @property
    def reward_name(self) -> str:
        return self.reward.name

    @property
    def reward_cost(self) -> int:
        return self.reward.cost


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    type = Column(String(40), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="notifications")


class UserStat(Base):
    __tablename__ = "user_stats"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True)
    total_tasks_completed = Column(Integer, default=0, nullable=False)
    total_xp = Column(Integer, default=0, nullable=False)
    average_rating = Column(Integer, default=0, nullable=False)
    achievements_count = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class XPTransaction(Base):
    __tablename__ = "xp_transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    reason = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="xp_transactions")


class DailyStreak(Base):
    __tablename__ = "daily_streaks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True)
    current_streak = Column(Integer, default=0, nullable=False)
    longest_streak = Column(Integer, default=0, nullable=False)
    last_completed_date = Column(String(20), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AdventurePoint(Base):
    """A configurable, family-wide point on the children's adventure map."""

    __tablename__ = "adventure_points"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    family_id = Column(String(36), ForeignKey("families.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=False, default="🗺️")
    image = Column(String(500), nullable=True)
    position_x = Column(Float, nullable=False, default=50)
    position_y = Column(Float, nullable=False, default=50)
    order_index = Column(Integer, nullable=False, default=0)
    required_xp = Column(Integer, nullable=False, default=0)
    required_level = Column(Integer, nullable=True)
    reward_xp = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    family = relationship("Family", back_populates="adventure_points")

    @property
    def name(self) -> str:
        """Compatibility alias for clients that call the point title a name."""
        return self.title

    @property
    def order(self) -> int:
        return self.order_index


class AdventurePointClaim(Base):
    __tablename__ = "adventure_point_claims"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    point_id = Column(String(36), ForeignKey("adventure_points.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    claimed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("point_id", "user_id", name="uq_adventure_point_claim"),)
