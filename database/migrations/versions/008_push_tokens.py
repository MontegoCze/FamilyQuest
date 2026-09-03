"""Store device tokens for push notifications."""

from alembic import op
import sqlalchemy as sa


revision = "008_push_tokens"
down_revision = "007_adventure_point_claims"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "push_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token", sa.String(512), nullable=False, unique=True),
        sa.Column("platform", sa.String(20), nullable=False, server_default="android"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_push_tokens_id", "push_tokens", ["id"], unique=False)
    op.create_index("ix_push_tokens_user_id", "push_tokens", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_push_tokens_user_id", table_name="push_tokens")
    op.drop_index("ix_push_tokens_id", table_name="push_tokens")
    op.drop_table("push_tokens")
