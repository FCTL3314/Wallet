"""Initial migration

Revision ID: 001
Revises:
Create Date: 2026-02-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, index=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "currencies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(10), nullable=False),
        sa.Column("symbol", sa.String(5), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("code", "user_id", name="uq_currency_code_user"),
    )

    op.create_table(
        "storage_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("name", "user_id", name="uq_storage_location_name_user"),
    )

    op.create_table(
        "storage_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("storage_location_id", sa.Integer(), sa.ForeignKey("storage_locations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("currency_id", sa.Integer(), sa.ForeignKey("currencies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("storage_location_id", "currency_id", name="uq_storage_account_loc_cur"),
    )

    op.create_table(
        "income_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("name", "user_id", name="uq_income_source_name_user"),
    )

    op.create_table(
        "expense_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("monthly_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("is_tax", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_rent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("name", "user_id", name="uq_expense_category_name_user"),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("type", sa.Enum("income", "expense", name="transactiontype"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False, index=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("currency_id", sa.Integer(), sa.ForeignKey("currencies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("storage_account_id", sa.Integer(), sa.ForeignKey("storage_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("income_source_id", sa.Integer(), sa.ForeignKey("income_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("expense_category_id", sa.Integer(), sa.ForeignKey("expense_categories.id", ondelete="SET NULL"), nullable=True),
    )

    op.create_table(
        "balance_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("storage_account_id", sa.Integer(), sa.ForeignKey("storage_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False, index=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("balance_snapshots")
    op.drop_table("transactions")
    op.drop_table("expense_categories")
    op.drop_table("income_sources")
    op.drop_table("storage_accounts")
    op.drop_table("storage_locations")
    op.drop_table("currencies")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS transactiontype")
