import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator


class BalanceSnapshotCreate(BaseModel):
    storage_account_id: int
    date: datetime.date
    amount: Decimal

    @field_validator("amount")
    @classmethod
    def amount_non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("amount must be 0 or greater")
        return v


class BalanceSnapshotUpdate(BaseModel):
    storage_account_id: int | None = None
    date: datetime.date | None = None
    amount: Decimal | None = None

    @field_validator("amount")
    @classmethod
    def amount_non_negative(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < 0:
            raise ValueError("amount must be 0 or greater")
        return v


class BalanceSnapshotResponse(BaseModel):
    id: int
    storage_account_id: int
    date: datetime.date
    amount: Decimal

    model_config = {"from_attributes": True}
