"""Normalize task categories.

Revision ID: 003_task_categories
Revises: 002_familyquest_domain
"""

from alembic import op
import sqlalchemy as sa


revision = "003_task_categories"
down_revision = "002_familyquest_domain"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE tasks SET category = 'home' WHERE category IS NULL OR category NOT IN ('home', 'school')")
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.alter_column("category", existing_type=sa.String(120), nullable=False, server_default="home")
        batch_op.create_check_constraint("ck_tasks_category", "category IN ('home', 'school')")


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_constraint("ck_tasks_category", type_="check")
        batch_op.alter_column("category", existing_type=sa.String(120), nullable=True, server_default=None)
