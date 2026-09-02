"""Add safe family member management metadata."""

from alembic import op
import sqlalchemy as sa

revision = "005_family_invitations"
down_revision = "004_adventure_points"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("family_members")}
    if "updated_at" not in columns:
        op.add_column("family_members", sa.Column("updated_at", sa.DateTime(), nullable=True))
        op.execute("UPDATE family_members SET updated_at = created_at")
    op.create_table(
        "family_invitations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("family_id", sa.String(36), sa.ForeignKey("families.id"), nullable=False),
        sa.Column("invited_email", sa.String(255), nullable=False),
        sa.Column("invited_name", sa.String(255), nullable=False),
        sa.Column("token", sa.String(128), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_family_invitations_token", "family_invitations", ["token"], unique=True)
    op.create_index("ix_family_invitations_invited_email", "family_invitations", ["invited_email"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_family_invitations_invited_email", table_name="family_invitations")
    op.drop_index("ix_family_invitations_token", table_name="family_invitations")
    op.drop_table("family_invitations")
    op.drop_column("family_members", "updated_at")
