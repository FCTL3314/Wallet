from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Currency(Base):
    __tablename__ = "currencies"
    __table_args__ = (UniqueConstraint("code", "user_id", name="uq_currency_code_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10))
    symbol: Mapped[str] = mapped_column(String(5))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    user = relationship("User", back_populates="currencies")
    storage_accounts = relationship("StorageAccount", back_populates="currency")
