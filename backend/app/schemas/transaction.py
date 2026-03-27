import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, field_validator, model_validator

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

    @model_validator(mode="after")
    def check_mutually_exclusive(self) -> Self:
        if self.income_source_id is not None and self.expense_category_id is not None:
            raise ValueError(
                "income_source_id and expense_category_id are mutually exclusive"
            )
        return self


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

    @model_validator(mode="after")
    def check_mutually_exclusive(self) -> Self:
        if self.income_source_id is not None and self.expense_category_id is not None:
            raise ValueError(
                "income_source_id and expense_category_id are mutually exclusive"
            )
        return self


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
