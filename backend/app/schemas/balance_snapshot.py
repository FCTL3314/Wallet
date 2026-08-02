import datetime
from decimal import Decimal

from pydantic import BaseModel


# A snapshot states what an account holds, not how much moved. Zero is a real
# balance and a credit card or margin account is legitimately negative, so
# unlike a transaction amount this field carries no sign constraint.
class BalanceSnapshotCreate(BaseModel):
    storage_account_id: int
    date: datetime.date
    amount: Decimal


class BalanceSnapshotUpdate(BaseModel):
    storage_account_id: int | None = None
    date: datetime.date | None = None
    amount: Decimal | None = None


class BalanceSnapshotResponse(BaseModel):
    id: int
    storage_account_id: int
    date: datetime.date
    amount: Decimal

    model_config = {"from_attributes": True}
