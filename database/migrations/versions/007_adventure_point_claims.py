"""Track claimed adventure point rewards.

Revision ID: 007_adventure_point_claims
Revises: 006_invitation_roles
"""

from alembic import op
import sqlalchemy as sa


revision = "007_adventure_point_claims"
down_revision = "006_invitation_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "adventure_point_claims",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("point_id", sa.String(36), sa.ForeignKey("adventure_points.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("claimed_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("point_id", "user_id", name="uq_adventure_point_claim"),
    )
    op.create_index("ix_adventure_point_claims_id", "adventure_point_claims", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_adventure_point_claims_id", table_name="adventure_point_claims")
    op.drop_table("adventure_point_claims")
