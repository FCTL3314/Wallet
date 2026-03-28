"""Add app_state singleton table."""

import sqlalchemy as sa
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "app_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "catalog_initial_sync_done",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.CheckConstraint("id = 1", name="ck_app_state_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("app_state")
