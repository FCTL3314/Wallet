from datetime import date
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Currency, Transaction, IncomeSource
from app.models.transaction import TransactionType
from app.services.analytics.periods import GroupBy, _period_label


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
) -> list[dict]:
    period = _period_label(group_by).label("period")
    q = (
        select(
            period,
            IncomeSource.name.label("source"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .join(
            IncomeSource, Transaction.income_source_id == IncomeSource.id, isouter=True
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
