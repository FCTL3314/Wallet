from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction, BalanceSnapshot, ExpenseCategory
from app.services.analytics.periods import GroupBy, _generate_periods
from app.services.analytics.balance import get_balance_timeline, totals_by_currency
from app.services.analytics.income import get_income_matrix
from app.services.analytics.metrics import (
    MetricAccumulator,
    compute_period_metrics,
    growth_stat,
    pct_change,
)
from app.services.analytics.money import build_converter, build_rate_coverage


async def get_summary(
    db: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
    group_by: GroupBy,
    currency_id: int | None = None,
    convert_to: str | None = None,
) -> dict:
    """
    Excel-model summary: profit = balance_change, derived_expense = income - profit.
    Generates one row per calendar period in the requested range.

    Every figure here comes from ``compute_period_metrics``, the same function
    that backs ``explain_period``, so a row and its breakdown are the same
    computation rendered twice rather than two computations expected to agree.

    When ``convert_to`` is set (e.g. "USD"), all monetary values are converted to
    that currency at the rate current at each period's end.

    Returns ``{"periods": [...], "stats": {...}, "rate_coverage": {...}}``.
    """
    periods = _generate_periods(date_from, date_to, group_by)
    if not periods:
        return {"periods": [], "stats": None, "rate_coverage": None}

    # Periods are whole calendar units, so the income window has to span the
    # generated periods rather than the raw request. Asking for "15 Mar - 2 Aug"
    # renders a full March row whose balance delta covers the whole month;
    # counting income only from the 15th would understate that row's expense.
    range_start, range_end = periods[0][0], periods[-1][1]
    period_ends = [end for _, end in periods]

    converter = await build_converter(db, user_id, convert_to, period_ends, currency_id)

    income = await get_income_matrix(
        db, user_id, range_start, range_end, group_by, currency_id
    )

    # Balances at every period end, plus the day before the first period, in one query
    prev_end = range_start - timedelta(days=1)
    timeline = await get_balance_timeline(
        db, user_id, [prev_end] + period_ends, currency_id
    )

    prev_accounts = timeline.balances_at(prev_end)
    initial_balances = totals_by_currency(prev_accounts)

    accumulator = MetricAccumulator()
    rows: list[dict] = []
    last_balances: dict[str, Decimal] = {}

    for period_start, period_end in periods:
        cur_accounts = timeline.balances_at(period_end)
        metrics = compute_period_metrics(
            period_start=period_start,
            period_end=period_end,
            prev_accounts=prev_accounts,
            cur_accounts=cur_accounts,
            income_by_currency=income.by_currency(period_start.isoformat()),
            remeasured_accounts=timeline.remeasured_accounts(period_start, period_end),
            converter=converter,
        )
        accumulator.add(metrics)

        row = metrics.as_row(include_converted=converter.converting)
        row["avg_income"] = accumulator.avg_income
        row["avg_profit"] = accumulator.avg_profit
        row["avg_expense"] = accumulator.avg_expense
        rows.append(row)

        prev_accounts = cur_accounts
        last_balances = metrics.balances

    stats = _build_stats(
        accumulator, initial_balances, last_balances, converter, range_end
    )

    rate_coverage = (
        await build_rate_coverage(db, user_id, converter.target)
        if converter.converting
        else None
    )

    return {"periods": rows, "stats": stats, "rate_coverage": rate_coverage}


def _build_stats(
    accumulator: MetricAccumulator,
    initial_balances: dict[str, Decimal],
    last_balances: dict[str, Decimal],
    converter,
    range_end: date,
) -> dict:
    balance_growth_delta: dict[str, Decimal] = {}
    balance_growth_pct: dict[str, Decimal | None] = {}
    for code in set(last_balances) | set(initial_balances):
        final = last_balances.get(code, Decimal("0"))
        initial = initial_balances.get(code, Decimal("0"))
        balance_growth_delta[code] = final - initial
        balance_growth_pct[code] = pct_change(final, initial)

    balance_growth_converted = None
    if converter.converting:
        initial_total = converter.collapse(initial_balances, range_end)
        final_total = converter.collapse(last_balances, range_end)
        balance_growth_converted = {
            "delta": final_total - initial_total,
            "pct": pct_change(final_total, initial_total),
            "currency": converter.target,
        }

    return {
        "income_growth": growth_stat(accumulator.income_active_periods, "income"),
        "profit_growth": growth_stat(accumulator.profit_active_periods, "profit"),
        "balance_growth": {
            "delta": balance_growth_delta,
            "pct": balance_growth_pct,
        },
        "balance_growth_converted": balance_growth_converted,
        "total_income": accumulator.total_income,
        "total_profit": accumulator.accountable_profit,
        "total_expense": accumulator.accountable_expense,
        "avg_income": accumulator.avg_income,
        "avg_profit": accumulator.avg_profit,
        "avg_expense": accumulator.avg_expense,
        "accountable_period_count": accumulator.accountable_count,
        "income_period_count": accumulator.income_count,
    }


async def get_date_range(db: AsyncSession, user_id: int) -> dict:
    """Return the earliest and latest dates across transactions and balance snapshots."""
    tx_result = await db.execute(
        select(func.min(Transaction.date), func.max(Transaction.date)).where(
            Transaction.user_id == user_id
        )
    )
    tx_row = tx_result.one()

    snap_result = await db.execute(
        select(func.min(BalanceSnapshot.date), func.max(BalanceSnapshot.date)).where(
            BalanceSnapshot.user_id == user_id
        )
    )
    snap_row = snap_result.one()

    starts = [d for d in [tx_row[0], snap_row[0]] if d is not None]
    ends = [d for d in [tx_row[1], snap_row[1]] if d is not None]
    if not starts or not ends:
        return {"min_date": None, "max_date": None}

    return {"min_date": min(starts), "max_date": max(ends)}


async def get_expense_template(db: AsyncSession, user_id: int) -> dict:
    result = await db.execute(
        select(ExpenseCategory).where(ExpenseCategory.user_id == user_id)
    )
    categories = result.scalars().all()

    items = []
    total = Decimal("0")

    for cat in categories:
        items.append(
            {
                "id": cat.id,
                "name": cat.name,
                "budgeted_amount": cat.budgeted_amount,
                "tags": cat.tags,
            }
        )
        total += cat.budgeted_amount

    without_tax = sum(
        (cat.budgeted_amount for cat in categories if "tax" not in cat.tags),
        Decimal("0"),
    )

    return {
        "items": items,
        "total": total,
        "without_tax": without_tax,
    }
