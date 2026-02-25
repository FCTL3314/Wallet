"""Rename monthly_amount to budgeted_amount in expense_categories

Revision ID: 003
Revises: 002
Create Date: 2026-02-24

"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("expense_categories", "monthly_amount", new_column_name="budgeted_amount")


def downgrade() -> None:
    op.alter_column("expense_categories", "budgeted_amount", new_column_name="monthly_amount")
