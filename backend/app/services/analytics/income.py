from datetime import date
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Currency, Transaction, IncomeSource
from app.models.transaction import TransactionType
from app.services.analytics.periods import GroupBy, _period_label, _generate_periods
from app.services.exchange_rates import (
    RateResult,
    get_rates_for_periods,
    convert_amount,
)


async def _get_income_per_period(
    db: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
    group_by: GroupBy,
    currency_id: int | None = None,
) -> dict[str, Decimal]:
    """Return total income per period as {period_start_iso: amount}."""
    period = func.date_trunc(group_by.value, Transaction.date).label("period")
    q = (
        select(period, func.coalesce(func.sum(Transaction.amount), 0).label("income"))
        .where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.income,
            Transaction.date >= date_from,
            Transaction.date <= date_to,
        )
        .group_by("period")
    )
    if currency_id is not None:
        q = q.where(Transaction.currency_id == currency_id)
    result = await db.execute(q)
    return {
        row.period.date().isoformat(): Decimal(str(row.income)) for row in result.all()
    }


async def _get_income_per_period_by_currency(
    db: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
    group_by: GroupBy,
) -> dict[str, dict[str, Decimal]]:
    """Return income per period broken down by currency: {period_key: {currency_code: amount}}."""
    period = func.date_trunc(group_by.value, Transaction.date).label("period")
    q = (
        select(
            period,
            Currency.code.label("currency_code"),
            func.coalesce(func.sum(Transaction.amount), 0).label("income"),
        )
        .join(Currency, Transaction.currency_id == Currency.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.income,
            Transaction.date >= date_from,
            Transaction.date <= date_to,
        )
        .group_by("period", Currency.code)
    )
    result = await db.execute(q)
    out: dict[str, dict[str, Decimal]] = {}
    for row in result.all():
        p = row.period.date().isoformat()
        if p not in out:
            out[p] = {}
        out[p][row.currency_code] = Decimal(str(row.income))
    return out


async def get_income_by_source(
    db: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
    group_by: GroupBy,
    currency_id: int | None = None,
    convert_to: str | None = None,
) -> list[dict]:
    converting = convert_to is not None and currency_id is None

    period = _period_label(group_by).label("period")

    if converting:
        q = (
            select(
                period,
                IncomeSource.name.label("source"),
                Currency.code.label("currency_code"),
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
    else:
        q = (
            select(
                period,
                IncomeSource.name.label("source"),
                func.coalesce(func.sum(Transaction.amount), 0).label("total"),
            )
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
            .group_by("period", IncomeSource.name)
            .order_by("period")
        )
        if currency_id is not None:
            q = q.where(Transaction.currency_id == currency_id)

    result = await db.execute(q)
    rows = result.all()

    if not converting:
        grouped: dict[str, dict] = {}
        for row in rows:
            p = row.period.date().isoformat() if row.period else "unknown"
            if p not in grouped:
                grouped[p] = {"period": p, "total": Decimal("0"), "sources": {}}
            source = row.source or "Other"
            amount = Decimal(str(row.total))
            grouped[p]["sources"][source] = amount
            grouped[p]["total"] += amount
        return list(grouped.values())

    # Converting mode: accumulate per-currency amounts per (period, source), then convert.
    # temp_data: {period_key: {source: {currency_code: amount}}}
    temp_data: dict[str, dict[str, dict[str, Decimal]]] = {}
    periods_with_data: set[date] = set()

    all_periods = _generate_periods(date_from, date_to, group_by)
    period_end_map: dict[str, date] = {
        start.isoformat(): end for start, end in all_periods
    }

    for row in rows:
        p = row.period.date().isoformat() if row.period else "unknown"
        period_end = period_end_map.get(p)
        if period_end:
            periods_with_data.add(period_end)
        source = row.source or "Other"
        amount = Decimal(str(row.total))
        if p not in temp_data:
            temp_data[p] = {}
        if source not in temp_data[p]:
            temp_data[p][source] = {}
        temp_data[p][source][row.currency_code] = (
            temp_data[p][source].get(row.currency_code, Decimal("0")) + amount
        )

    # Fetch all currency codes the user owns (needed for rate lookup)
    codes_result = await db.execute(
        select(Currency.code).where(Currency.user_id == user_id)
    )
    all_codes = list(codes_result.scalars())

    rate_cache: dict[date, dict[str, RateResult]] = {}
    if periods_with_data and all_codes:
        rate_cache = await get_rates_for_periods(
            db,
            all_codes,
            list(periods_with_data),
            to_code=convert_to,
            user_id=user_id,
        )

    converted: dict[str, dict] = {}
    for p, sources_map in temp_data.items():
        period_end = period_end_map.get(p)
        rate_map = rate_cache.get(period_end, {}) if period_end else {}
        if p not in converted:
            converted[p] = {"period": p, "total": Decimal("0"), "sources": {}}
        for source, per_currency in sources_map.items():
            amount = convert_amount(per_currency, rate_map, convert_to)
            converted[p]["sources"][source] = amount
            converted[p]["total"] += amount

    return list(converted.values())
