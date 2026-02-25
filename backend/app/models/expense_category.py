from decimal import Decimal

from sqlalchemy import String, ForeignKey, Numeric, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ExpenseCategory(Base):
    __tablename__ = "expense_categories"
    __table_args__ = (UniqueConstraint("name", "user_id", name="uq_expense_category_name_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    budgeted_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    is_tax: Mapped[bool] = mapped_column(Boolean, default=False)
    is_rent: Mapped[bool] = mapped_column(Boolean, default=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    user = relationship("User", back_populates="expense_categories")
    transactions = relationship("Transaction", back_populates="expense_category")
