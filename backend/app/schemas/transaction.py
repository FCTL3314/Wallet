from __future__ import annotations

import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator

from app.models.transaction import TransactionType


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
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return v


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
        if v is not None and v <= 0:
            raise ValueError("amount must be greater than 0")
        return v


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
