from decimal import Decimal


def validate_amount_positive(v: Decimal) -> Decimal:
    if v <= 0:
        raise ValueError("amount must be greater than 0")
    return v


def validate_amount_non_negative(v: Decimal) -> Decimal:
    if v < 0:
        raise ValueError("amount must be 0 or greater")
    return v
