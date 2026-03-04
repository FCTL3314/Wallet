import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator

from app.schemas._validators import validate_amount_positive


class BalanceSnapshotCreate(BaseModel):
    storage_account_id: int
    date: datetime.date
    amount: Decimal

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        return validate_amount_positive(v)


class BalanceSnapshotUpdate(BaseModel):
    storage_account_id: int | None = None
    date: datetime.date | None = None
    amount: Decimal | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal | None) -> Decimal | None:
        return validate_amount_positive(v) if v is not None else v


class BalanceSnapshotResponse(BaseModel):
    id: int
    storage_account_id: int
    date: datetime.date
    amount: Decimal

    model_config = {"from_attributes": True}
