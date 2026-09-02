"""Add FamilyQuest domain tables.

Revision ID: 002_familyquest_domain
Revises: 001_initial_schema
"""

from alembic import op
import sqlalchemy as sa


revision = "002_familyquest_domain"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def _id_index(table: str) -> None:
    op.create_index(f"ix_{table}_id", table, ["id"], unique=False)


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("family_id", sa.String(36), sa.ForeignKey("families.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("category", sa.String(120)),
        sa.Column("difficulty", sa.Integer, nullable=False, server_default="1"),
        sa.Column("xp", sa.Integer, nullable=False, server_default="10"),
        sa.Column("repeat_mode", sa.String(20), nullable=False, server_default="once"),
        sa.Column("due_time", sa.String(20)),
        sa.Column("due_date", sa.String(50)),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    _id_index("tasks")
    op.create_table(
        "task_assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("task_id", "user_id", name="uq_task_assignment"),
    )
    _id_index("task_assignments")
    op.create_table(
        "task_completions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("completed_at", sa.DateTime, nullable=False),
        sa.Column("reviewed_at", sa.DateTime),
        sa.Column("notes", sa.Text),
    )
    _id_index("task_completions")
    op.create_table(
        "task_ratings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("completion_id", sa.String(36), sa.ForeignKey("task_completions.id"), nullable=False, unique=True),
        sa.Column("rated_by_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("value", sa.Integer, nullable=False),
        sa.Column("comment", sa.Text),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    _id_index("task_ratings")
    op.create_table(
        "achievements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("family_id", sa.String(36), sa.ForeignKey("families.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("icon", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("requirement", sa.Text, nullable=False),
        sa.Column("xp_reward", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    _id_index("achievements")
    op.create_table(
        "user_achievements",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("achievement_id", sa.String(36), sa.ForeignKey("achievements.id"), nullable=False),
        sa.Column("unlocked_at", sa.DateTime, nullable=True),
        sa.Column("progress", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_unlocked", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
    )
    _id_index("user_achievements")
    op.create_table(
        "rewards",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("family_id", sa.String(36), sa.ForeignKey("families.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("cost", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    _id_index("rewards")
    op.create_table(
        "reward_redemptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("reward_id", sa.String(36), sa.ForeignKey("rewards.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("requested_at", sa.DateTime, nullable=False),
        sa.Column("reviewed_at", sa.DateTime),
    )
    _id_index("reward_redemptions")
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    _id_index("notifications")
    op.create_table(
        "user_stats",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("total_tasks_completed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_xp", sa.Integer, nullable=False, server_default="0"),
        sa.Column("average_rating", sa.Integer, nullable=False, server_default="0"),
        sa.Column("achievements_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    _id_index("user_stats")
    op.create_table(
        "xp_transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    _id_index("xp_transactions")
    op.create_table(
        "daily_streaks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("current_streak", sa.Integer, nullable=False, server_default="0"),
        sa.Column("longest_streak", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_completed_date", sa.String(20)),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    _id_index("daily_streaks")


def downgrade() -> None:
    for table in (
        "daily_streaks", "xp_transactions", "user_stats", "notifications",
        "reward_redemptions", "rewards", "user_achievements", "achievements",
        "task_ratings", "task_completions", "task_assignments", "tasks",
    ):
        op.drop_index(f"ix_{table}_id", table_name=table)
        op.drop_table(table)
