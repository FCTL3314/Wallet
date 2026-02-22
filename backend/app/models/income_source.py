from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class IncomeSource(Base):
    __tablename__ = "income_sources"
    __table_args__ = (UniqueConstraint("name", "user_id", name="uq_income_source_name_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    user = relationship("User", back_populates="income_sources")
    transactions = relationship("Transaction", back_populates="income_source")
