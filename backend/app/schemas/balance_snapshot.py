from __future__ import annotations

import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator


class BalanceSnapshotCreate(BaseModel):
    storage_account_id: int
    date: datetime.date
    amount: Decimal

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return v


class BalanceSnapshotUpdate(BaseModel):
    date: datetime.date | None = None
    amount: Decimal | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("amount must be greater than 0")
        return v


class BalanceSnapshotResponse(BaseModel):
    id: int
    storage_account_id: int
    date: datetime.date
    amount: Decimal

    model_config = {"from_attributes": True}
