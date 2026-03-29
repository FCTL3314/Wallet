from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Currency(Base):
    __tablename__ = "currencies"
    __table_args__ = (
        UniqueConstraint("code", "user_id", name="uq_currency_code_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10))
    symbol: Mapped[str] = mapped_column(String(5))
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    catalog_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("currency_catalog.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    user = relationship("User", back_populates="currencies")
    storage_accounts = relationship("StorageAccount", back_populates="currency")

    @property
    def is_custom(self) -> bool:
        return self.catalog_id is None

    def __str__(self) -> str:
        return f"{self.code} ({self.symbol})"
