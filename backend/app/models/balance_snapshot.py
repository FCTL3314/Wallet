from datetime import date
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BalanceSnapshot(Base):
    __tablename__ = "balance_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    storage_account_id: Mapped[int] = mapped_column(ForeignKey("storage_accounts.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))

    user = relationship("User", back_populates="balance_snapshots")
    storage_account = relationship("StorageAccount", back_populates="balance_snapshots")
