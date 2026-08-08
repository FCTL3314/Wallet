from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Currency
from app.services.exchange_rates import (
    RateResult,
    convert_amount_detailed,
    get_rates_batch,
    get_rates_for_periods,
)


@dataclass(frozen=True)
class CollapsedAmount:
    """A per-currency map reduced to one number, plus what had to be dropped."""

    value: Decimal
    missing: list[str]


class MoneyConverter:
    """Reduces per-currency amounts to a single comparable number.

    Every analytics figure that spans more than one currency goes through one of
    these. Before it existed each caller carried its own ``if converting:`` fork,
    which is how the same period could be summed at one rate in the summary table
    and at another in the row that explained it.

    With no target currency the converter is a plain sum. That is only correct
    when the caller has already narrowed to a single currency, which the API layer
    guarantees by rejecting multi-currency requests that name no target.
    """

    def __init__(
        self,
        target: str | None,
        rates: dict[date, dict[str, RateResult]] | None = None,
    ) -> None:
        self._target = target
        self._rates = rates or {}

    @property
    def target(self) -> str | None:
        return self._target

    @property
    def converting(self) -> bool:
        return self._target is not None

    def rates_at(self, at: date) -> dict[str, RateResult]:
        return self._rates.get(at, {})

    def collapse_detailed(
        self, per_currency: dict[str, Decimal], at: date
    ) -> CollapsedAmount:
        if not self.converting:
            return CollapsedAmount(sum(per_currency.values(), Decimal("0")), [])
        value, missing = convert_amount_detailed(
            per_currency, self.rates_at(at), self._target
        )
        return CollapsedAmount(value, missing)

    def collapse(self, per_currency: dict[str, Decimal], at: date) -> Decimal:
        return self.collapse_detailed(per_currency, at).value


async def user_currency_codes(db: AsyncSession, user_id: int) -> list[str]:
    result = await db.execute(select(Currency.code).where(Currency.user_id == user_id))
    return list(result.scalars())


async def build_converter(
    db: AsyncSession,
    user_id: int,
    convert_to: str | None,
    at_dates: list[date],
    currency_id: int | None = None,
) -> MoneyConverter:
    """Build a converter holding every rate the caller will need, in one batch.

    A request already narrowed to one currency is never converted, whatever
    ``convert_to`` says — that rule lives here alone so no endpoint can apply it
    differently.

    Rates are resolved per date rather than once for the whole range: a period is
    valued at the rate that was current when it closed, so re-running an old
    report does not reprice it with today's quote.
    """
    target = None if currency_id is not None else convert_to
    if target is None:
        return MoneyConverter(None)

    codes = await user_currency_codes(db, user_id)
    if not codes or not at_dates:
        return MoneyConverter(target)

    rates = await get_rates_for_periods(
        db, codes, at_dates, to_code=target, user_id=user_id
    )
    return MoneyConverter(target, rates)


async def build_rate_coverage(
    db: AsyncSession, user_id: int, base_currency: str
) -> dict:
    """Report whether every currency the user holds can be priced in ``base_currency``."""
    codes = await user_currency_codes(db, user_id)
    non_base_codes = [c for c in codes if c != base_currency]

    if not non_base_codes:
        return {
            "base_currency": base_currency,
            "currencies": {},
            "conversion_available": True,
        }

    rate_map = await get_rates_batch(
        db, non_base_codes, to_code=base_currency, user_id=user_id
    )

    currencies: dict[str, dict] = {}
    all_ok = True
    for code in non_base_codes:
        rr = rate_map.get(code)
        if rr is None:
            currencies[code] = {
                "status": "missing",
                "valid_date": None,
                "source": "none",
                "rate": None,
            }
            all_ok = False
            continue
        currencies[code] = {
            "status": rr.status,
            "valid_date": rr.valid_date,
            "source": rr.source,
            "rate": str(rr.rate) if rr.rate is not None else None,
        }
        if rr.status != "ok":
            all_ok = False

    return {
        "base_currency": base_currency,
        "currencies": currencies,
        "conversion_available": all_ok,
    }
