import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# Minimal stub — needed so FK "users.id" resolves in metadata
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)


class Currency(Base):
    __tablename__ = "currencies"
    __table_args__ = (UniqueConstraint("code", "user_id", name="uq_currency_code_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10))
    symbol: Mapped[str] = mapped_column(String(5))
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    storage_accounts: Mapped[list["StorageAccount"]] = relationship(back_populates="currency")


class StorageLocation(Base):
    __tablename__ = "storage_locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    storage_accounts: Mapped[list["StorageAccount"]] = relationship(back_populates="storage_location")


class StorageAccount(Base):
    __tablename__ = "storage_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    storage_location_id: Mapped[int] = mapped_column(
        ForeignKey("storage_locations.id", ondelete="CASCADE")
    )
    currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    storage_location: Mapped["StorageLocation"] = relationship(back_populates="storage_accounts")
    currency: Mapped["Currency"] = relationship(back_populates="storage_accounts")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="storage_account")
    balance_snapshots: Mapped[list["BalanceSnapshot"]] = relationship(back_populates="storage_account")


class IncomeSource(Base):
    __tablename__ = "income_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="income_source")


class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    budgeted_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    tags: Mapped[list] = mapped_column(JSON, default=list)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="expense_category")


class TransactionType(str, enum.Enum):
    income = "income"
    expense = "expense"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType))
    date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    currency_id: Mapped[int] = mapped_column(ForeignKey("currencies.id", ondelete="CASCADE"))
    storage_account_id: Mapped[int] = mapped_column(
        ForeignKey("storage_accounts.id", ondelete="CASCADE")
    )
    income_source_id: Mapped[int | None] = mapped_column(
        ForeignKey("income_sources.id", ondelete="SET NULL"), nullable=True
    )
    expense_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("expense_categories.id", ondelete="SET NULL"), nullable=True
    )

    currency: Mapped["Currency"] = relationship()
    storage_account: Mapped["StorageAccount"] = relationship(back_populates="transactions")
    income_source: Mapped["IncomeSource | None"] = relationship(back_populates="transactions")
    expense_category: Mapped["ExpenseCategory | None"] = relationship(back_populates="transactions")


class BalanceSnapshot(Base):
    __tablename__ = "balance_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    storage_account_id: Mapped[int] = mapped_column(
        ForeignKey("storage_accounts.id", ondelete="CASCADE")
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))

    storage_account: Mapped["StorageAccount"] = relationship(back_populates="balance_snapshots")
