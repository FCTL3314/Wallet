from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Currency, Transaction, IncomeSource
from app.models.transaction import TransactionType
from app.services.analytics.money import build_converter
from app.services.analytics.periods import GroupBy, _period_label, _generate_periods

OTHER_SOURCE = "Other"


@dataclass
class IncomeMatrix:
    """Income at its finest grain: period → source → currency.

    Every income figure Wallet reports is a rollup of this one table. Keeping the
    breakdown rather than pre-summing is what stops the dashboard total, the
    per-source donut and a single explained row from drifting apart — they are
    now three views of the same cells, not three queries that happen to agree.
    """

    cells: dict[str, dict[str, dict[str, Decimal]]] = field(default_factory=dict)

    def add(self, period: str, source: str, currency: str, amount: Decimal) -> None:
        by_source = self.cells.setdefault(period, {})
        by_currency = by_source.setdefault(source, {})
        by_currency[currency] = by_currency.get(currency, Decimal("0")) + amount

    def periods(self) -> list[str]:
        return sorted(self.cells)

    def by_source(self, period: str) -> dict[str, dict[str, Decimal]]:
        return self.cells.get(period, {})

    def by_currency(self, period: str) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for per_currency in self.cells.get(period, {}).values():
            for code, amount in per_currency.items():
                totals[code] = totals.get(code, Decimal("0")) + amount
        return totals


async def get_income_matrix(
    db: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
    group_by: GroupBy,
    currency_id: int | None = None,
) -> IncomeMatrix:
    """Load every income transaction in range, grouped by period, source and currency."""
    period = _period_label(group_by).label("period")
    q = (
        select(
            period,
            IncomeSource.name.label("source"),
            Currency.code.label("currency"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .join(Currency, Transaction.currency_id == Currency.id)
        .join(
            IncomeSource,
            Transaction.income_source_id == IncomeSource.id,
            isouter=True,
        )
        .where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.income,
            Transaction.date >= date_from,
            Transaction.date <= date_to,
        )
        .group_by("period", IncomeSource.name, Currency.code)
        .order_by("period")
    )
    if currency_id is not None:
        q = q.where(Transaction.currency_id == currency_id)

    result = await db.execute(q)

    matrix = IncomeMatrix()
    for row in result.all():
        if row.period is None:
            continue
        matrix.add(
            row.period.date().isoformat(),
            row.source or OTHER_SOURCE,
            row.currency,
            Decimal(str(row.total)),
        )
    return matrix


async def get_income_by_source(
    db: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
    group_by: GroupBy,
    currency_id: int | None = None,
    convert_to: str | None = None,
) -> dict:
    """Income split by source, per period and across the whole range.

    The range totals ship with the periods so a caller charting the split never
    re-adds them itself — that second sum is what let a donut disagree with the
    total income the summary reported for the same window.
    """
    all_periods = _generate_periods(date_from, date_to, group_by)
    if not all_periods:
        return {"periods": [], "totals": {}, "total": Decimal("0")}

    # Match get_summary: rows are whole calendar periods, so the income window
    # spans them rather than the raw request, or a mid-month date_from would make
    # this endpoint disagree with the summary it sits next to.
    range_start, range_end = all_periods[0][0], all_periods[-1][1]
    period_end_map = {start.isoformat(): end for start, end in all_periods}

    converter = await build_converter(
        db, user_id, convert_to, list(period_end_map.values()), currency_id
    )
    matrix = await get_income_matrix(
        db, user_id, range_start, range_end, group_by, currency_id
    )

    periods: list[dict] = []
    range_totals: dict[str, Decimal] = {}
    range_total = Decimal("0")

    for period_key in matrix.periods():
        period_end = period_end_map.get(period_key)
        if period_end is None:
            continue
        sources: dict[str, Decimal] = {}
        period_total = Decimal("0")
        for source, per_currency in matrix.by_source(period_key).items():
            # Each period converts at its own closing rate, so the range total has
            # to accumulate the converted amounts rather than be re-derived from
            # the raw currency sums at a single rate.
            amount = converter.collapse(per_currency, period_end)
            sources[source] = amount
            period_total += amount
            range_totals[source] = range_totals.get(source, Decimal("0")) + amount
        range_total += period_total
        periods.append(
            {"period": period_key, "total": period_total, "sources": sources}
        )

    return {"periods": periods, "totals": range_totals, "total": range_total}
