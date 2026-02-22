from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StorageLocation(Base):
    __tablename__ = "storage_locations"
    __table_args__ = (UniqueConstraint("name", "user_id", name="uq_storage_location_name_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    user = relationship("User", back_populates="storage_locations")
    storage_accounts = relationship("StorageAccount", back_populates="storage_location", cascade="all, delete-orphan")


class StorageAccount(Base):
    __tablename__ = "storage_accounts"
    __table_args__ = (
        UniqueConstraint("storage_location_id", "currency_id", name="uq_storage_account_loc_cur"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    storage_location_id: Mapped[int] = mapped_column(ForeignKey("storage_locations.id", ondelete="CASCADE"))
    currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    user = relationship("User", back_populates="storage_accounts")
    storage_location = relationship("StorageLocation", back_populates="storage_accounts")
    currency = relationship("Currency", back_populates="storage_accounts")
    transactions = relationship("Transaction", back_populates="storage_account")
    balance_snapshots = relationship("BalanceSnapshot", back_populates="storage_account")
