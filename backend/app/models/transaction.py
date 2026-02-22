import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, Date, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


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
    storage_account_id: Mapped[int] = mapped_column(ForeignKey("storage_accounts.id", ondelete="CASCADE"))
    income_source_id: Mapped[int | None] = mapped_column(
        ForeignKey("income_sources.id", ondelete="SET NULL"), nullable=True
    )
    expense_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("expense_categories.id", ondelete="SET NULL"), nullable=True
    )

    user = relationship("User", back_populates="transactions")
    currency = relationship("Currency")
    storage_account = relationship("StorageAccount", back_populates="transactions")
    income_source = relationship("IncomeSource", back_populates="transactions")
    expense_category = relationship("ExpenseCategory", back_populates="transactions")
