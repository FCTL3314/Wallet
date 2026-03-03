from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction, BalanceSnapshot, ExpenseCategory, Currency, StorageAccount, StorageLocation, IncomeSource
from app.models.transaction import TransactionType


class GroupBy(str, Enum):
    month = "month"
    quarter = "quarter"
    year = "year"


def _period_label(group_by: GroupBy):
    """Return SQL date_trunc expression for Transaction.date depending on grouping."""
    return func.date_trunc(group_by.value, Transaction.date)


def _generate_periods(date_from: date, date_to: date, group_by: GroupBy) -> list[tuple[date, date]]:
    """Generate (period_start, period_end) tuples covering the date range."""
    periods = []
    if group_by == GroupBy.month:
        cur = date(date_from.year, date_from.month, 1)
        while cur <= date_to:
            end = date(cur.year, cur.month, monthrange(cur.year, cur.month)[1])
            periods.append((cur, end))
            if cur.month == 12:
                cur = date(cur.year + 1, 1, 1)
            else:
                cur = date(cur.year, cur.month + 1, 1)
    elif group_by == GroupBy.quarter:
        qstart_month = ((date_from.month - 1) // 3) * 3 + 1
        cur = date(date_from.year, qstart_month, 1)
        while cur <= date_to:
            end_month = cur.month + 2
            end = date(cur.year, end_month, monthrange(cur.year, end_month)[1])
            periods.append((cur, end))
            if cur.month >= 10:
                cur = date(cur.year + 1, 1, 1)
            else:
                cur = date(cur.year, cur.month + 3, 1)
    else:  # year
        cur = date(date_from.year, 1, 1)
        while cur <= date_to:
            end = date(cur.year, 12, 31)
            periods.append((cur, end))
            cur = date(cur.year + 1, 1, 1)
    return periods


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
        row.period.date().isoformat(): Decimal(str(row.income))
        for row in result.all()
    }


async def get_summary(
    db: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
    group_by: GroupBy,
    currency_id: int | None = None,
) -> list[dict]:
    """
    Excel-model summary: profit = balance_change, derived_expense = profit - income.
    Generates one row per calendar period in the requested range.
    """
    periods = _generate_periods(date_from, date_to, group_by)
    if not periods:
        return []

    income_map = await _get_income_per_period(db, user_id, date_from, date_to, group_by, currency_id)

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
            cur: cur_balances.get(cur, Decimal("0")) - prev_balances.get(cur, Decimal("0"))
            for cur in all_currencies
        }

        profit = sum(balance_change.values(), Decimal("0"))
        derived_expense = profit - income

        if income > 0:
            cumulative_income += income
            income_count += 1
        if profit > 0:
            cumulative_profit += profit
            profit_count += 1

        avg_income = (cumulative_income / income_count).quantize(Decimal("0.01")) if income_count > 0 else Decimal("0")
        avg_profit = (cumulative_profit / profit_count).quantize(Decimal("0.01")) if profit_count > 0 else Decimal("0")

        summary.append({
            "period": period_key,
            "income": income,
            "profit": profit,
            "derived_expense": derived_expense,
            "avg_income": avg_income,
            "avg_profit": avg_profit,
            "balances": cur_balances,
            "balance_change": balance_change,
        })

        prev_balances = cur_balances

    return summary


async def _get_balance_at_date(db: AsyncSession, user_id: int, at_date: date, currency_id: int | None = None) -> dict:
    """Get the latest balance snapshot per currency up to at_date."""
    subq = (
        select(
            BalanceSnapshot.storage_account_id,
            func.max(BalanceSnapshot.date).label("max_date"),
        )
        .where(BalanceSnapshot.user_id == user_id, BalanceSnapshot.date <= at_date)
        .group_by(BalanceSnapshot.storage_account_id)
        .subquery()
    )

    q = (
        select(Currency.code, func.sum(BalanceSnapshot.amount).label("total"))
        .join(subq, and_(
            BalanceSnapshot.storage_account_id == subq.c.storage_account_id,
            BalanceSnapshot.date == subq.c.max_date,
        ))
        .join(StorageAccount, BalanceSnapshot.storage_account_id == StorageAccount.id)
        .join(Currency, StorageAccount.currency_id == Currency.id)
        .where(BalanceSnapshot.user_id == user_id)
        .group_by(Currency.code)
    )
    if currency_id is not None:
        q = q.where(Currency.id == currency_id)
    result = await db.execute(q)
    return {row.code: Decimal(str(row.total)) for row in result.all()}


async def get_income_by_source(
    db: AsyncSession, user_id: int, date_from: date, date_to: date, group_by: GroupBy,
    currency_id: int | None = None,
) -> list[dict]:
    period = _period_label(group_by).label("period")
    q = (
        select(
            period,
            IncomeSource.name.label("source"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .join(IncomeSource, Transaction.income_source_id == IncomeSource.id, isouter=True)
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


async def get_balance_by_storage(
    db: AsyncSession, user_id: int, date_from: date, date_to: date, group_by: GroupBy
) -> list[dict]:
    """For each period, get balance per storage account from the latest snapshot in that period."""
    period = (
        func.date_trunc(group_by.value, BalanceSnapshot.date)
    ).label("period")

    subq = (
        select(
            period,
            BalanceSnapshot.storage_account_id,
            func.max(BalanceSnapshot.date).label("max_date"),
        )
        .where(
            BalanceSnapshot.user_id == user_id,
            BalanceSnapshot.date >= date_from,
            BalanceSnapshot.date <= date_to,
        )
        .group_by("period", BalanceSnapshot.storage_account_id)
        .subquery()
    )

    q = (
        select(
            subq.c.period,
            StorageLocation.name.label("location"),
            Currency.code.label("currency"),
            BalanceSnapshot.amount,
        )
        .join(subq, and_(
            BalanceSnapshot.storage_account_id == subq.c.storage_account_id,
            BalanceSnapshot.date == subq.c.max_date,
        ))
        .join(StorageAccount, BalanceSnapshot.storage_account_id == StorageAccount.id)
        .join(StorageLocation, StorageAccount.storage_location_id == StorageLocation.id)
        .join(Currency, StorageAccount.currency_id == Currency.id)
        .where(BalanceSnapshot.user_id == user_id)
        .order_by(subq.c.period)
    )
    result = await db.execute(q)
    rows = result.all()

    grouped: dict[str, dict] = {}
    for row in rows:
        p = row.period.date().isoformat() if row.period else "unknown"
        if p not in grouped:
            grouped[p] = {"period": p, "accounts": [], "totals": {}}
        acc_name = f"{row.location} {row.currency}"
        amount = Decimal(str(row.amount))
        grouped[p]["accounts"].append({"name": acc_name, "currency": row.currency, "amount": amount})
        grouped[p]["totals"][row.currency] = grouped[p]["totals"].get(row.currency, Decimal("0")) + amount

    return list(grouped.values())


async def get_expense_vs_budget(db: AsyncSession, user_id: int, year: int, month: int) -> list[dict]:
    result = await db.execute(
        select(ExpenseCategory).where(ExpenseCategory.user_id == user_id).order_by(ExpenseCategory.name)
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


async def get_balance_breakdown(db: AsyncSession, user_id: int) -> list[dict]:
    """
    Return the latest balance snapshot per StorageAccount for the given user up to today.

    Each item contains: account_id, account_label (location name + currency code),
    currency code, the date of the latest snapshot, and its amount.
    """
    today = date.today()

    subq = (
        select(
            BalanceSnapshot.storage_account_id,
            func.max(BalanceSnapshot.date).label("max_date"),
        )
        .where(BalanceSnapshot.user_id == user_id, BalanceSnapshot.date <= today)
        .group_by(BalanceSnapshot.storage_account_id)
        .subquery()
    )

    q = (
        select(
            StorageAccount.id.label("account_id"),
            StorageLocation.name.label("location_name"),
            Currency.code.label("currency"),
            subq.c.max_date.label("latest_snapshot_date"),
            BalanceSnapshot.amount.label("latest_snapshot_amount"),
        )
        .join(subq, and_(
            BalanceSnapshot.storage_account_id == subq.c.storage_account_id,
            BalanceSnapshot.date == subq.c.max_date,
        ))
        .join(StorageAccount, BalanceSnapshot.storage_account_id == StorageAccount.id)
        .join(StorageLocation, StorageAccount.storage_location_id == StorageLocation.id)
        .join(Currency, StorageAccount.currency_id == Currency.id)
        .where(BalanceSnapshot.user_id == user_id)
        .order_by(StorageLocation.name, Currency.code)
    )

    result = await db.execute(q)
    rows = result.all()

    return [
        {
            "account_id": row.account_id,
            "account_label": f"{row.location_name} {row.currency}",
            "currency": row.currency,
            "latest_snapshot_date": row.latest_snapshot_date,
            "latest_snapshot_amount": Decimal(str(row.latest_snapshot_amount)),
        }
        for row in rows
    ]


async def get_expense_template(db: AsyncSession, user_id: int) -> dict:
    result = await db.execute(select(ExpenseCategory).where(ExpenseCategory.user_id == user_id))
    categories = result.scalars().all()

    items = []
    total = Decimal("0")
    tax_amount = Decimal("0")
    rent_amount = Decimal("0")

    for cat in categories:
        items.append({
            "id": cat.id,
            "name": cat.name,
            "budgeted_amount": cat.budgeted_amount,
            "is_tax": cat.is_tax,
            "is_rent": cat.is_rent,
        })
        total += cat.budgeted_amount
        if cat.is_tax:
            tax_amount += cat.budgeted_amount
        if cat.is_rent:
            rent_amount += cat.budgeted_amount

    return {
        "items": items,
        "total": total,
        "without_tax": total - tax_amount,
        "without_rent": total - rent_amount,
        "without_tax_and_rent": total - tax_amount - rent_amount,
    }
