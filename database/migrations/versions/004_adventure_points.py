"""Add family-scoped adventure map points.

Revision ID: 004_adventure_points
Revises: 003_task_categories
"""

from alembic import op
import sqlalchemy as sa


revision = "004_adventure_points"
down_revision = "003_task_categories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "adventure_points",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("family_id", sa.String(36), sa.ForeignKey("families.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("icon", sa.String(50), nullable=False, server_default="🗺️"),
        sa.Column("image", sa.String(500)),
        sa.Column("position_x", sa.Float, nullable=False, server_default="50"),
        sa.Column("position_y", sa.Float, nullable=False, server_default="50"),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("required_xp", sa.Integer, nullable=False, server_default="0"),
        sa.Column("required_level", sa.Integer),
        sa.Column("reward_xp", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_adventure_points_id", "adventure_points", ["id"], unique=False)
    op.create_index("ix_adventure_points_family_id", "adventure_points", ["family_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_adventure_points_family_id", table_name="adventure_points")
    op.drop_index("ix_adventure_points_id", table_name="adventure_points")
    op.drop_table("adventure_points")
