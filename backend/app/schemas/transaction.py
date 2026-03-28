import datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, model_validator

from app.models.transaction import TransactionType
from app.schemas._validators import AmountPositiveMixin


class TransactionCreate(AmountPositiveMixin, BaseModel):
    type: TransactionType
    date: datetime.date
    amount: Decimal
    description: str | None = None
    currency_id: int
    storage_account_id: int
    income_source_id: int | None = None
    expense_category_id: int | None = None

    @model_validator(mode="after")
    def check_mutually_exclusive(self) -> Self:
        if self.income_source_id is not None and self.expense_category_id is not None:
            raise ValueError(
                "income_source_id and expense_category_id are mutually exclusive"
            )
        return self


class TransactionUpdate(AmountPositiveMixin, BaseModel):
    type: TransactionType | None = None
    date: datetime.date | None = None
    amount: Decimal | None = None
    description: str | None = None
    currency_id: int | None = None
    storage_account_id: int | None = None
    income_source_id: int | None = None
    expense_category_id: int | None = None

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
