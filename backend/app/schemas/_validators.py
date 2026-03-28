from decimal import Decimal

from pydantic import field_validator


def validate_amount_positive(v: Decimal) -> Decimal:
    if v <= 0:
        raise ValueError("amount must be greater than 0")
    return v


def validate_amount_non_negative(v: Decimal) -> Decimal:
    if v < 0:
        raise ValueError("amount must be 0 or greater")
    return v


class AmountPositiveMixin:
    """Mixin that validates `amount` is strictly positive (> 0).

    Inherit before BaseModel in Create schemas, or alongside it in Update schemas
    where `amount` is optional (None passes through without validation).
    """

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None:
            return validate_amount_positive(v)
        return v


class AmountNonNegativeMixin:
    """Mixin that validates `amount` is non-negative (>= 0).

    Inherit before BaseModel in Create schemas, or alongside it in Update schemas
    where `amount` is optional (None passes through without validation).
    """

    @field_validator("amount")
    @classmethod
    def amount_must_be_non_negative(cls, v: Decimal | None) -> Decimal | None:
        if v is not None:
            return validate_amount_non_negative(v)
        return v
