"""Replace is_tax/is_rent with tags JSON column

Revision ID: 004
Revises: 003
Create Date: 2026-03-03

"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "expense_categories",
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.execute("""
        UPDATE expense_categories SET tags = (
            CASE WHEN is_tax AND is_rent THEN '["tax","rent"]'::json
                 WHEN is_tax THEN '["tax"]'::json
                 WHEN is_rent THEN '["rent"]'::json
                 ELSE '[]'::json END)
    """)
    op.drop_column("expense_categories", "is_tax")
    op.drop_column("expense_categories", "is_rent")


def downgrade():
    op.add_column(
        "expense_categories",
        sa.Column("is_tax", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "expense_categories",
        sa.Column("is_rent", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.execute(
        "UPDATE expense_categories SET is_tax = tags::jsonb ? 'tax', is_rent = tags::jsonb ? 'rent'"
    )
    op.drop_column("expense_categories", "tags")
