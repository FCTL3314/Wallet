"""Add currency catalog, exchange rates, and update currencies table."""

import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade():
    # currency_catalog
    op.create_table(
        "currency_catalog",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("symbol", sa.String(10), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("currency_type", sa.String(10), nullable=False),
        sa.Column("coingecko_id", sa.String(100), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "currency_type IN ('fiat', 'crypto')", name="ck_currency_catalog_type"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_currency_catalog_code"),
    )

    # catalog_sync_history
    op.create_table(
        "catalog_sync_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(30), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entries_upserted", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # exchange_rates
    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("from_code", sa.String(20), nullable=False),
        sa.Column(
            "to_code", sa.String(20), nullable=False, server_default=sa.text("'USD'")
        ),
        sa.Column("rate", sa.Numeric(28, 12), nullable=False),
        sa.Column("valid_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "from_code", "to_code", "valid_date", name="uq_exchange_rates_code_date"
        ),
    )
    op.create_index(
        "ix_exchange_rates_from_date",
        "exchange_rates",
        ["from_code", "valid_date"],
    )

    # user_exchange_rates
    op.create_table(
        "user_exchange_rates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_code", sa.String(20), nullable=False),
        sa.Column(
            "to_code", sa.String(20), nullable=False, server_default=sa.text("'USD'")
        ),
        sa.Column("rate", sa.Numeric(28, 12), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "from_code",
            "to_code",
            "valid_from",
            name="uq_user_exchange_rates",
        ),
    )
    op.create_index(
        "ix_user_exchange_rates_user_from_date",
        "user_exchange_rates",
        ["user_id", "from_code", "valid_from"],
    )

    # Alter currencies table
    op.add_column(
        "currencies",
        sa.Column(
            "catalog_id",
            sa.Integer(),
            sa.ForeignKey("currency_catalog.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "currencies",
        sa.Column("name", sa.String(100), nullable=True),
    )


def downgrade():
    op.drop_column("currencies", "name")
    op.drop_column("currencies", "catalog_id")

    op.drop_index(
        "ix_user_exchange_rates_user_from_date", table_name="user_exchange_rates"
    )
    op.drop_table("user_exchange_rates")

    op.drop_index("ix_exchange_rates_from_date", table_name="exchange_rates")
    op.drop_table("exchange_rates")

    op.drop_table("catalog_sync_history")
    op.drop_table("currency_catalog")
