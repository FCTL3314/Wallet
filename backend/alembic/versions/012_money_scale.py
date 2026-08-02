"""Widen transaction and snapshot amounts to 8 decimal places.

Numeric(14, 2) silently rounded any crypto balance below 0.005 to zero, even
though the currency catalog offers crypto and the UI badges it as such.
Widening only adds precision, so existing fiat rows are unaffected.
"""

import sqlalchemy as sa
from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None

_TABLES = ("transactions", "balance_snapshots")


def upgrade():
    for table in _TABLES:
        op.alter_column(
            table,
            "amount",
            existing_type=sa.Numeric(14, 2),
            type_=sa.Numeric(28, 8),
            existing_nullable=False,
        )


def downgrade():
    for table in _TABLES:
        op.alter_column(
            table,
            "amount",
            existing_type=sa.Numeric(28, 8),
            type_=sa.Numeric(14, 2),
            existing_nullable=False,
        )
