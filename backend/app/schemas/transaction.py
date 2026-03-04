import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator

from app.models.transaction import TransactionType
from app.schemas._validators import validate_amount_positive


class TransactionCreate(BaseModel):
    type: TransactionType
    date: datetime.date
    amount: Decimal
    description: str | None = None
    currency_id: int
    storage_account_id: int
    income_source_id: int | None = None
    expense_category_id: int | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        return validate_amount_positive(v)


class TransactionUpdate(BaseModel):
    type: TransactionType | None = None
    date: datetime.date | None = None
    amount: Decimal | None = None
    description: str | None = None
    currency_id: int | None = None
    storage_account_id: int | None = None
    income_source_id: int | None = None
    expense_category_id: int | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal | None) -> Decimal | None:
        return validate_amount_positive(v) if v is not None else v


class TransactionResponse(BaseModel):
    id: int
    type: TransactionType
    date: datetime.date
    amount: Decimal
    description: str | None
    currency_id: int
    storage_account_id: int
    income_source_id: int | None
    expense_category_id: int | None

    model_config = {"from_attributes": True}
