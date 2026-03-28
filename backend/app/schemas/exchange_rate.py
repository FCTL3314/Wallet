from datetime import date
from decimal import Decimal

from pydantic import BaseModel, field_validator

from app.schemas._validators import validate_amount_positive


class UserExchangeRateCreate(BaseModel):
    to_code: str = "USD"
    rate: Decimal
    valid_from: date
    valid_to: date | None = None

    @field_validator("rate")
    @classmethod
    def rate_must_be_positive(cls, v: Decimal) -> Decimal:
        return validate_amount_positive(v)


class UserExchangeRateResponse(BaseModel):
    id: int
    from_code: str
    to_code: str
    rate: Decimal
    valid_from: date
    valid_to: date | None

    model_config = {"from_attributes": True}


class RateInfoResponse(BaseModel):
    status: str  # "ok" | "stale" | "missing"
    valid_date: date | None
    source: str
    rate: Decimal | None


class RateCoverageEntry(BaseModel):
    status: str
    valid_date: date | None
    source: str


class RateCoverageResponse(BaseModel):
    base_currency: str
    currencies: dict[str, RateCoverageEntry]
    conversion_available: bool
