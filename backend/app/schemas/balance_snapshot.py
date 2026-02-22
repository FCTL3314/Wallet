from __future__ import annotations

import datetime
from decimal import Decimal

from pydantic import BaseModel


class BalanceSnapshotCreate(BaseModel):
    storage_account_id: int
    date: datetime.date
    amount: Decimal


class BalanceSnapshotUpdate(BaseModel):
    date: datetime.date | None = None
    amount: Decimal | None = None


class BalanceSnapshotResponse(BaseModel):
    id: int
    storage_account_id: int
    date: datetime.date
    amount: Decimal

    model_config = {"from_attributes": True}
