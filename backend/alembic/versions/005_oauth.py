"""Add GitHub and Google OAuth columns to users table."""

import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("github_id", sa.BigInteger(), nullable=True),
    )
    op.create_unique_constraint("uq_users_github_id", "users", ["github_id"])
    op.create_index("ix_users_github_id", "users", ["github_id"])

    op.add_column(
        "users",
        sa.Column("google_sub", sa.String(255), nullable=True),
    )
    op.create_unique_constraint("uq_users_google_sub", "users", ["google_sub"])
    op.create_index("ix_users_google_sub", "users", ["google_sub"])

    op.alter_column(
        "users", "password_hash", existing_type=sa.String(255), nullable=True
    )


def downgrade():
    op.alter_column(
        "users", "password_hash", existing_type=sa.String(255), nullable=False
    )

    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_constraint("uq_users_google_sub", "users", type_="unique")
    op.drop_column("users", "google_sub")

    op.drop_index("ix_users_github_id", table_name="users")
    op.drop_constraint("uq_users_github_id", "users", type_="unique")
    op.drop_column("users", "github_id")
