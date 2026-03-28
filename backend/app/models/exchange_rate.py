from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_code: Mapped[str] = mapped_column(String(20), nullable=False)
    to_code: Mapped[str] = mapped_column(String(20), nullable=False, default="USD")
    rate: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    valid_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "from_code", "to_code", "valid_date", name="uq_exchange_rates_code_date"
        ),
        Index("ix_exchange_rates_from_date", "from_code", "valid_date"),
    )


class UserExchangeRate(Base):
    __tablename__ = "user_exchange_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    from_code: Mapped[str] = mapped_column(String(20), nullable=False)
    to_code: Mapped[str] = mapped_column(String(20), nullable=False, default="USD")
    rate: Mapped[Decimal] = mapped_column(Numeric(28, 12), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "from_code",
            "to_code",
            "valid_from",
            name="uq_user_exchange_rates",
        ),
        Index(
            "ix_user_exchange_rates_user_from_date",
            "user_id",
            "from_code",
            "valid_from",
        ),
    )
