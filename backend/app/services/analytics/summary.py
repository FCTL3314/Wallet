from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction, BalanceSnapshot, ExpenseCategory
from app.services.analytics.periods import GroupBy, _generate_periods
from app.services.analytics.balance import _get_balance_at_date
from app.services.analytics.income import _get_income_per_period


async def get_summary(
    db: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
    group_by: GroupBy,
    currency_id: int | None = None,
) -> list[dict]:
    """
    Excel-model summary: profit = balance_change, derived_expense = income - profit.
    Generates one row per calendar period in the requested range.
    """
    periods = _generate_periods(date_from, date_to, group_by)
    if not periods:
        return []

    income_map = await _get_income_per_period(
        db, user_id, date_from, date_to, group_by, currency_id
    )

    # Balance at the end of the period immediately before the first period
    prev_end = periods[0][0] - timedelta(days=1)
    prev_balances = await _get_balance_at_date(db, user_id, prev_end, currency_id)

    summary = []
    cumulative_income = Decimal("0")
    cumulative_profit = Decimal("0")
    income_count = 0
    profit_count = 0

    for period_start, period_end in periods:
        period_key = period_start.isoformat()
        income = income_map.get(period_key, Decimal("0"))

        cur_balances = await _get_balance_at_date(db, user_id, period_end, currency_id)

        all_currencies = set(cur_balances) | set(prev_balances)
        balance_change = {
            cur: cur_balances.get(cur, Decimal("0"))
            - prev_balances.get(cur, Decimal("0"))
            for cur in all_currencies
        }

        profit = sum(balance_change.values(), Decimal("0"))
        # Detect bootstrap period: no prior snapshots, so balance_change = initial capital entry.
        is_bootstrap = (
            not prev_balances and sum(cur_balances.values(), Decimal("0")) > 0
        )
        derived_expense = (
            Decimal("0") if is_bootstrap else max(Decimal("0"), income - profit)
        )

        if not is_bootstrap:
            if income > 0:
                cumulative_income += income
                income_count += 1
            if profit > 0:
                cumulative_profit += profit
                profit_count += 1

        avg_income = (
            (cumulative_income / income_count).quantize(Decimal("0.01"))
            if income_count > 0
            else Decimal("0")
        )
        avg_profit = (
            (cumulative_profit / profit_count).quantize(Decimal("0.01"))
            if profit_count > 0
            else Decimal("0")
        )

        summary.append(
            {
                "period": period_key,
                "income": income,
                "profit": profit,
                "derived_expense": derived_expense,
                "avg_income": avg_income,
                "avg_profit": avg_profit,
                "balances": cur_balances,
                "balance_change": balance_change,
                "is_bootstrap": is_bootstrap,
            }
        )

        prev_balances = cur_balances

    return summary


async def get_expense_vs_budget(
    db: AsyncSession, user_id: int, year: int, month: int
) -> list[dict]:
    result = await db.execute(
        select(ExpenseCategory)
        .where(ExpenseCategory.user_id == user_id)
        .order_by(ExpenseCategory.name)
    )
    rows = result.scalars().all()

    return [
        {
            "id": row.id,
            "name": row.name,
            "budgeted": Decimal(str(row.budgeted_amount)),
            "actual": Decimal("0"),
            "remaining": Decimal(str(row.budgeted_amount)),
        }
        for row in rows
    ]


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

    dates = [
        d for d in [tx_row[0], tx_row[1], snap_row[0], snap_row[1]] if d is not None
    ]
    if not dates:
        return {"min_date": None, "max_date": None}

    min_date = min(d for d in [tx_row[0], snap_row[0]] if d is not None)
    max_date = max(d for d in [tx_row[1], snap_row[1]] if d is not None)
    return {"min_date": min_date, "max_date": max_date}


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

    return {
        "items": items,
        "total": total,
    }
