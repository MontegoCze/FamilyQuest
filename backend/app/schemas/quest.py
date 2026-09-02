from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


def clean_text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Value must not be empty")
    return value


class ChildCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    password: str = Field(..., min_length=8, max_length=128)
    email: str | None = Field(default=None, max_length=255)

    _clean_name = field_validator("full_name")(clean_text)


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    category: Literal["home", "school"] = "home"
    difficulty: int = Field(default=1, ge=1, le=5)
    xp: int | None = Field(default=None, ge=1, le=10000)
    repeat_mode: Literal["once", "daily", "weekdays", "weekends", "custom"] = "once"
    due_time: str | None = Field(default=None, max_length=20)
    due_date: str | None = Field(default=None, max_length=50)
    assignee_ids: list[str] = Field(default_factory=list, max_length=50)

    _clean_title = field_validator("title")(clean_text)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    category: Literal["home", "school"] | None = None
    difficulty: int | None = Field(default=None, ge=1, le=5)
    xp: int | None = Field(default=None, ge=1, le=10000)
    repeat_mode: Literal["once", "daily", "weekdays", "weekends", "custom"] | None = None
    due_time: str | None = Field(default=None, max_length=20)
    due_date: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None
    assignee_ids: list[str] | None = Field(default=None, max_length=50)


class TaskRead(BaseModel):
    id: str
    family_id: str
    title: str
    description: str | None
    category: str | None
    difficulty: int
    xp: int
    repeat_mode: str
    due_time: str | None
    due_date: str | None
    created_by: str
    is_active: bool
    assignments: list["AssignmentRead"] = []
    completions: list["CompletionRead"] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssignmentRead(BaseModel):
    id: str
    task_id: str
    user_id: str
    assigned_at: datetime
    user_name: str | None = None

    model_config = {"from_attributes": True}


class AssignmentCreate(BaseModel):
    user_ids: list[str] = Field(..., min_length=1, max_length=50)


class CompletionCreate(BaseModel):
    notes: str | None = Field(default=None, max_length=4000)


class CompletionReview(BaseModel):
    status: Literal["approved", "rejected"]
    notes: str | None = Field(default=None, max_length=4000)


class CompletionRead(BaseModel):
    id: str
    task_id: str
    user_id: str
    status: str
    completed_at: datetime
    reviewed_at: datetime | None
    notes: str | None

    model_config = {"from_attributes": True}


class RatingCreate(BaseModel):
    value: int = Field(..., ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class AchievementCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    icon: str = Field(default="🏆", max_length=50)
    description: str = Field(..., min_length=2, max_length=2000)
    requirement: str = Field(..., min_length=1, max_length=255)
    xp_reward: int = Field(default=0, ge=0, le=10000)


class AchievementUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    icon: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, min_length=2, max_length=2000)
    requirement: str | None = Field(default=None, min_length=1, max_length=255)
    xp_reward: int | None = Field(default=None, ge=0, le=10000)


class AchievementRead(BaseModel):
    id: str
    family_id: str
    name: str
    icon: str
    description: str
    requirement: str
    xp_reward: int
    progress: int = 0
    is_unlocked: bool = False
    unlocked_at: datetime | None = None

    model_config = {"from_attributes": True}


class RewardCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    cost: int = Field(..., ge=1, le=1_000_000)
    is_active: bool = True


class RewardRead(BaseModel):
    id: str
    family_id: str
    name: str
    description: str | None
    cost: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RedemptionRead(BaseModel):
    id: str
    reward_id: str
    user_id: str
    status: str
    requested_at: datetime
    reviewed_at: datetime | None
    reward_name: str | None = None
    reward_cost: int | None = None

    model_config = {"from_attributes": True}


class RedemptionReview(BaseModel):
    status: Literal["approved", "rejected"]


class NotificationRead(BaseModel):
    id: str
    user_id: str
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class StatsRead(BaseModel):
    user_id: str
    total_tasks_completed: int
    total_xp: int
    level: int
    xp_in_level: int
    xp_for_next_level: int
    average_rating: float
    achievements_count: int
    current_streak: int
    longest_streak: int
    pending_completions: int


class AdventurePointCreate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    icon: str = Field(default="🗺️", min_length=1, max_length=50)
    image: str | None = Field(default=None, max_length=500)
    position_x: float = Field(default=50, ge=0, le=100)
    position_y: float = Field(default=50, ge=0, le=100)
    order_index: int | None = Field(default=None, ge=0, le=100000)
    order: int | None = Field(default=None, ge=0, le=100000)
    required_xp: int = Field(default=0, ge=0, le=1_000_000)
    required_level: int | None = Field(default=None, ge=1, le=1000)
    reward_xp: int = Field(default=0, ge=0, le=1_000_000)
    is_active: bool = True

    @model_validator(mode="after")
    def title_from_name(self):
        if not self.title and not self.name:
            raise ValueError("A title or name is required.")
        if not self.title:
            self.title = self.name
        if self.order_index is None:
            self.order_index = self.order
        return self


class AdventurePointUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    icon: str | None = Field(default=None, min_length=1, max_length=50)
    image: str | None = Field(default=None, max_length=500)
    position_x: float | None = Field(default=None, ge=0, le=100)
    position_y: float | None = Field(default=None, ge=0, le=100)
    order_index: int | None = Field(default=None, ge=0, le=100000)
    order: int | None = Field(default=None, ge=0, le=100000)
    required_xp: int | None = Field(default=None, ge=0, le=1_000_000)
    required_level: int | None = Field(default=None, ge=1, le=1000)
    reward_xp: int | None = Field(default=None, ge=0, le=1_000_000)
    is_active: bool | None = None

    @model_validator(mode="after")
    def title_from_name(self):
        if self.title is None and self.name is not None:
            self.title = self.name
        if self.order_index is None:
            self.order_index = self.order
        return self


class AdventureReorder(BaseModel):
    point_ids: list[str] = Field(..., min_length=1, max_length=500)


class AdventurePointRead(BaseModel):
    id: str
    family_id: str
    title: str
    name: str | None = None
    description: str | None
    icon: str
    image: str | None
    position_x: float
    position_y: float
    order_index: int
    order: int | None = None
    required_xp: int
    required_level: int | None
    reward_xp: int
    is_active: bool
    status: str = "locked"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


TaskRead.model_rebuild()
