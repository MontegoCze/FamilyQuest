"""Add roles to family invitations."""

from alembic import op
import sqlalchemy as sa

revision = "006_invitation_roles"
down_revision = "005_family_invitations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "family_invitations",
        sa.Column("role", sa.String(20), nullable=False, server_default="child"),
    )


def downgrade() -> None:
    op.drop_column("family_invitations", "role")
