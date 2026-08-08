from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFound
from app.models import (
    Currency,
    IncomeSource,
    StorageAccount,
    StorageLocation,
    Transaction,
)
from app.models.transaction import TransactionType
from app.services.analytics.balance import (
    AccountBalance,
    account_directory,
    account_label,
    get_balance_timeline,
)
from app.services.analytics.income import get_income_matrix
from app.services.analytics.metrics import account_movements, compute_period_metrics
from app.services.analytics.money import build_converter
from app.services.analytics.periods import GroupBy, _generate_periods


def _snapshot_ref(balance: AccountBalance | None) -> dict | None:
    if balance is None:
        return None
    return {"date": balance.as_of, "amount": balance.amount}


async def _income_rows(
    db: AsyncSession,
    user_id: int,
    start: date,
    end: date,
    currency_id: int | None,
) -> list[dict]:
    """The individual transactions behind a period's income, for display only.

    The period's income *total* is not summed from these rows — it comes from the
    shared income matrix, the same source the summary row uses.
    """
    q = (
        select(
            Transaction.id,
            Transaction.date,
            Transaction.amount,
            Transaction.description,
            Currency.code.label("currency"),
            IncomeSource.name.label("source"),
            StorageLocation.name.label("location"),
        )
        .join(Currency, Transaction.currency_id == Currency.id)
        .join(
            IncomeSource, Transaction.income_source_id == IncomeSource.id, isouter=True
        )
        .join(StorageAccount, Transaction.storage_account_id == StorageAccount.id)
        .join(StorageLocation, StorageAccount.storage_location_id == StorageLocation.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.income,
            Transaction.date >= start,
            Transaction.date <= end,
        )
        .order_by(Transaction.date, Transaction.id)
    )
    if currency_id is not None:
        q = q.where(Transaction.currency_id == currency_id)

    result = await db.execute(q)
    return [
        {
            "id": row.id,
            "date": row.date,
            "amount": row.amount,
            "currency": row.currency,
            "source": row.source or "Other",
            "account": f"{row.location} {row.currency}",
            "description": row.description,
        }
        for row in result.all()
    ]


async def explain_period(
    db: AsyncSession,
    user_id: int,
    period: date,
    group_by: GroupBy,
    currency_id: int | None = None,
    convert_to: str | None = None,
) -> dict:
    """Show where a single summary row's numbers came from.

    The figures are not recomputed here: this calls ``compute_period_metrics``
    with the same inputs ``get_summary`` gives it, then attaches the snapshots and
    transactions behind them. A breakdown that disagreed with the row it explains
    is therefore not expressible.
    """
    periods = _generate_periods(period, period, group_by)
    if not periods:
        raise ResourceNotFound("period")
    start, end = periods[0]
    prev_end = start - timedelta(days=1)

    converter = await build_converter(db, user_id, convert_to, [end], currency_id)

    timeline = await get_balance_timeline(db, user_id, [prev_end, end], currency_id)
    prev_accounts = timeline.balances_at(prev_end)
    cur_accounts = timeline.balances_at(end)
    remeasured = timeline.remeasured_accounts(start, end)

    income = await get_income_matrix(db, user_id, start, end, group_by, currency_id)
    income_by_currency = income.by_currency(start.isoformat())

    metrics = compute_period_metrics(
        period_start=start,
        period_end=end,
        prev_accounts=prev_accounts,
        cur_accounts=cur_accounts,
        income_by_currency=income_by_currency,
        remeasured_accounts=remeasured,
        converter=converter,
    )

    directory = await account_directory(db, user_id)
    accounts = [
        {
            "account_id": movement.account_id,
            "label": account_label(directory, movement.account_id),
            "currency": movement.currency,
            "opening": _snapshot_ref(movement.opening),
            "closing": _snapshot_ref(movement.closing),
            "delta": movement.delta,
            "is_opening_capital": movement.is_opening_capital,
            "remeasured_in_period": movement.account_id in remeasured,
        }
        for movement in account_movements(prev_accounts, cur_accounts)
    ]

    return {
        "period": metrics.period,
        "period_start": start,
        "period_end": end,
        "is_bootstrap": metrics.is_bootstrap,
        "is_measured": metrics.is_measured,
        "currency": converter.target,
        "accounts": accounts,
        "income_transactions": await _income_rows(db, user_id, start, end, currency_id),
        "income_by_currency": income_by_currency,
        "balance_change": metrics.balance_change,
        "opening_capital": metrics.opening_capital,
        "balances": metrics.balances,
        "income": metrics.income,
        "profit": metrics.profit,
        "derived_expense": metrics.derived_expense,
        "conversion_missing": metrics.conversion_missing,
        "rates": {
            code: {
                "rate": rr.rate,
                "source": rr.source,
                "valid_date": rr.valid_date,
                "status": rr.status,
            }
            for code, rr in converter.rates_at(end).items()
        },
    }
