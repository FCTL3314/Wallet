import calendar
from datetime import date, date as date_type, timedelta
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction, BalanceSnapshot, ExpenseCategory
from app.models.transaction import TransactionType
from app.services.analytics.periods import GroupBy, _generate_periods
from app.services.analytics.balance import _get_balance_at_date
from app.services.analytics.income import _get_income_per_period


def _pct(new: Decimal, old: Decimal) -> Decimal | None:
    """Return percentage change from old to new, rounded to 2 dp, or None if old is zero."""
    if old == 0:
        return None
    return ((new - old) / old * 100).quantize(Decimal("0.01"))


async def get_summary(
    db: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
    group_by: GroupBy,
    currency_id: int | None = None,
) -> dict:
    """
    Excel-model summary: profit = balance_change, derived_expense = income - profit.
    Generates one row per calendar period in the requested range.

    Returns ``{"periods": [...], "stats": {...}}``.
    """
    periods = _generate_periods(date_from, date_to, group_by)
    if not periods:
        return {"periods": [], "stats": None}

    income_map = await _get_income_per_period(
        db, user_id, date_from, date_to, group_by, currency_id
    )

    # Balance at the end of the period immediately before the first period
    prev_end = periods[0][0] - timedelta(days=1)
    prev_balances = await _get_balance_at_date(db, user_id, prev_end, currency_id)

    # Save initial balances for balance_growth stat (before any period mutations)
    initial_balances = dict(prev_balances)

    summary = []
    cumulative_income = Decimal("0")
    cumulative_profit = Decimal("0")
    income_count = 0
    profit_count = 0

    # Data collected for growth stats
    income_active_periods: list[dict] = []  # periods where income > 0 and not bootstrap
    profit_active_periods: list[
        dict
    ] = []  # periods where (income > 0 or profit != 0) and not bootstrap
    last_cur_balances: dict[str, Decimal] = {}

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
                income_active_periods.append(
                    {"period": period_key, "income": income, "profit": profit}
                )
            if income > 0 or profit != 0:
                cumulative_profit += profit
                profit_count += 1
                profit_active_periods.append(
                    {"period": period_key, "income": income, "profit": profit}
                )

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
        last_cur_balances = cur_balances

    # --- Compute stats ---

    # income_growth: first vs last income-active period
    income_growth = None
    if len(income_active_periods) >= 2:
        first = income_active_periods[0]
        last = income_active_periods[-1]
        delta = last["income"] - first["income"]
        income_growth = {
            "delta": delta,
            "pct": _pct(last["income"], first["income"]),
            "from_period": first["period"],
            "to_period": last["period"],
        }

    # profit_growth: first vs last profit-active period
    profit_growth = None
    if len(profit_active_periods) >= 2:
        first = profit_active_periods[0]
        last = profit_active_periods[-1]
        delta = last["profit"] - first["profit"]
        profit_growth = {
            "delta": delta,
            "pct": _pct(last["profit"], first["profit"]),
            "from_period": first["period"],
            "to_period": last["period"],
        }

    # balance_growth: initial_balances vs last period's cur_balances (per currency)
    all_balance_currencies = set(last_cur_balances) | set(initial_balances)
    balance_growth_delta: dict[str, Decimal] = {}
    balance_growth_pct: dict[str, Decimal | None] = {}
    for cur in all_balance_currencies:
        cur_val = last_cur_balances.get(cur, Decimal("0"))
        init_val = initial_balances.get(cur, Decimal("0"))
        balance_growth_delta[cur] = cur_val - init_val
        balance_growth_pct[cur] = _pct(cur_val, init_val)

    stats = {
        "income_growth": income_growth,
        "profit_growth": profit_growth,
        "balance_growth": {
            "delta": balance_growth_delta,
            "pct": balance_growth_pct,
        },
        "total_income": cumulative_income,
        "total_profit": cumulative_profit,
        "active_period_count": profit_count,
        "income_period_count": income_count,
    }

    return {"periods": summary, "stats": stats}


async def get_expense_vs_budget(
    db: AsyncSession, user_id: int, year: int, month: int
) -> list[dict]:
    date_from = date_type(year, month, 1)
    date_to = date_type(year, month, calendar.monthrange(year, month)[1])

    cats = (
        (
            await db.execute(
                select(ExpenseCategory)
                .where(ExpenseCategory.user_id == user_id)
                .order_by(ExpenseCategory.name)
            )
        )
        .scalars()
        .all()
    )

    actuals_rows = (
        await db.execute(
            select(Transaction.expense_category_id, func.sum(Transaction.amount))
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.expense,
                Transaction.date.between(date_from, date_to),
                Transaction.expense_category_id.isnot(None),
            )
            .group_by(Transaction.expense_category_id)
        )
    ).all()
    actuals = {cat_id: amt for cat_id, amt in actuals_rows}

    return [
        {
            "id": row.id,
            "name": row.name,
            "budgeted": Decimal(str(row.budgeted_amount)),
            "actual": Decimal(str(actuals.get(row.id, 0))),
            "remaining": Decimal(str(row.budgeted_amount))
            - Decimal(str(actuals.get(row.id, 0))),
        }
        for row in cats
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

    without_tax = sum(
        (cat.budgeted_amount for cat in categories if "tax" not in cat.tags),
        Decimal("0"),
    )

    return {
        "items": items,
        "total": total,
        "without_tax": without_tax,
    }
