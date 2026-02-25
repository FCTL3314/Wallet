from datetime import date
from decimal import Decimal
from enum import Enum

from sqlalchemy import select, func, case, and_, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction, BalanceSnapshot, ExpenseCategory, Currency, StorageAccount, StorageLocation
from app.models.transaction import TransactionType


class GroupBy(str, Enum):
    month = "month"
    quarter = "quarter"
    year = "year"


def _period_label(group_by: GroupBy):
    """Return SQL expressions for (period_start, label) depending on grouping."""
    if group_by == GroupBy.month:
        return func.date_trunc("month", Transaction.date)
    elif group_by == GroupBy.quarter:
        return func.date_trunc("quarter", Transaction.date)
    else:
        return func.date_trunc("year", Transaction.date)


async def get_summary(
    db: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
    group_by: GroupBy,
) -> list[dict]:
    period = _period_label(group_by).label("period")
    income_sum = func.coalesce(
        func.sum(case((Transaction.type == TransactionType.income, Transaction.amount), else_=literal_column("0"))),
        0,
    ).label("income")
    expense_sum = func.coalesce(
        func.sum(case((Transaction.type == TransactionType.expense, Transaction.amount), else_=literal_column("0"))),
        0,
    ).label("expenses")

    q = (
        select(period, income_sum, expense_sum)
        .where(
            Transaction.user_id == user_id,
            Transaction.date >= date_from,
            Transaction.date <= date_to,
        )
        .group_by("period")
        .order_by("period")
    )
    result = await db.execute(q)
    rows = result.all()

    summary = []
    cumulative_income = Decimal("0")
    cumulative_profit = Decimal("0")
    for i, row in enumerate(rows, 1):
        income = Decimal(str(row.income))
        expenses = Decimal(str(row.expenses))
        profit = income - expenses
        cumulative_income += income
        cumulative_profit += profit
        summary.append({
            "period": row.period.date().isoformat() if row.period else None,
            "income": income,
            "expenses": expenses,
            "profit": profit,
            "avg_income": (cumulative_income / i).quantize(Decimal("0.01")),
            "avg_profit": (cumulative_profit / i).quantize(Decimal("0.01")),
        })

    # attach balance snapshots for each period
    for entry in summary:
        if entry["period"]:
            period_date = date.fromisoformat(entry["period"])
            if group_by == GroupBy.month:
                from calendar import monthrange
                end = date(period_date.year, period_date.month, monthrange(period_date.year, period_date.month)[1])
            elif group_by == GroupBy.quarter:
                qm = period_date.month + 2
                from calendar import monthrange
                end = date(period_date.year, qm, monthrange(period_date.year, qm)[1])
            else:
                end = date(period_date.year, 12, 31)

            balances = await _get_balance_at_date(db, user_id, end)
            entry["balances"] = balances

    return summary


async def _get_balance_at_date(db: AsyncSession, user_id: int, at_date: date) -> dict:
    """Get the latest balance snapshot for each currency up to at_date."""
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
    result = await db.execute(q)
    return {row.code: Decimal(str(row.total)) for row in result.all()}


async def get_income_by_source(
    db: AsyncSession, user_id: int, date_from: date, date_to: date, group_by: GroupBy
) -> list[dict]:
    from app.models import IncomeSource

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
    from app.models import BalanceSnapshot

    period = (
        func.date_trunc(group_by.value if group_by != GroupBy.month else "month", BalanceSnapshot.date)
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
    from calendar import monthrange

    date_from = date(year, month, 1)
    date_to = date(year, month, monthrange(year, month)[1])

    actuals_subq = (
        select(
            Transaction.expense_category_id,
            func.coalesce(func.sum(Transaction.amount), 0).label("actual"),
        )
        .where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.expense,
            Transaction.date >= date_from,
            Transaction.date <= date_to,
            Transaction.expense_category_id.isnot(None),
        )
        .group_by(Transaction.expense_category_id)
        .subquery()
    )

    q = (
        select(
            ExpenseCategory.id,
            ExpenseCategory.name,
            ExpenseCategory.budgeted_amount,
            func.coalesce(actuals_subq.c.actual, 0).label("actual"),
        )
        .outerjoin(actuals_subq, ExpenseCategory.id == actuals_subq.c.expense_category_id)
        .where(ExpenseCategory.user_id == user_id)
        .order_by(ExpenseCategory.name)
    )
    result = await db.execute(q)
    rows = result.all()

    return [
        {
            "id": row.id,
            "name": row.name,
            "budgeted": Decimal(str(row.budgeted_amount)),
            "actual": Decimal(str(row.actual)),
            "remaining": Decimal(str(row.budgeted_amount)) - Decimal(str(row.actual)),
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
