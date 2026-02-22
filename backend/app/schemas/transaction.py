from __future__ import annotations

import datetime
from decimal import Decimal

from pydantic import BaseModel

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


class TransactionUpdate(BaseModel):
    type: TransactionType | None = None
    date: datetime.date | None = None
    amount: Decimal | None = None
    description: str | None = None
    currency_id: int | None = None
    storage_account_id: int | None = None
    income_source_id: int | None = None
    expense_category_id: int | None = None


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
