"""Add base_currency_code to users."""

import sqlalchemy as sa
from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users", sa.Column("base_currency_code", sa.String(10), nullable=True)
    )


def downgrade():
    op.drop_column("users", "base_currency_code")
