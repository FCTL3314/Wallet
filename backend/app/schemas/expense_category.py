from decimal import Decimal

from pydantic import BaseModel


class ExpenseCategoryCreate(BaseModel):
    name: str
    budgeted_amount: Decimal = Decimal("0")
    tags: list[str] = []


class ExpenseCategoryUpdate(BaseModel):
    name: str | None = None
    budgeted_amount: Decimal | None = None
    tags: list[str] | None = None


class ExpenseCategoryResponse(BaseModel):
    id: int
    name: str
    budgeted_amount: Decimal
    tags: list[str]

    model_config = {"from_attributes": True}
