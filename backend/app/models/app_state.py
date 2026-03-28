from sqlalchemy import Boolean, CheckConstraint
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AppState(Base):
    """Single-row table holding application-wide runtime state.

    Only one row ever exists (id=1), enforced by a database CHECK constraint.
    Use AppState.load(db) to get-or-create the singleton instance.
    """

    __tablename__ = "app_state"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    catalog_initial_sync_done: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    rates_backfill_done: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    __table_args__ = (CheckConstraint("id = 1", name="ck_app_state_singleton"),)

    @classmethod
    async def load(cls, db: AsyncSession) -> "AppState":
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = (
            pg_insert(cls)
            .values(id=1, catalog_initial_sync_done=False, rates_backfill_done=False)
            .on_conflict_do_nothing(index_elements=["id"])
        )
        await db.execute(stmt)
        return await db.get(cls, 1)
