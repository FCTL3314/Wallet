from decimal import Decimal

from pydantic import BaseModel


class ExpenseCategoryCreate(BaseModel):
    name: str
    monthly_amount: Decimal = Decimal("0")
    is_tax: bool = False
    is_rent: bool = False


class ExpenseCategoryUpdate(BaseModel):
    name: str | None = None
    monthly_amount: Decimal | None = None
    is_tax: bool | None = None
    is_rent: bool | None = None


class ExpenseCategoryResponse(BaseModel):
    id: int
    name: str
    monthly_amount: Decimal
    is_tax: bool
    is_rent: bool

    model_config = {"from_attributes": True}
