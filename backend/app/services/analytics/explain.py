from datetime import date, timedelta
from decimal import Decimal

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
    get_balance_timeline,
    totals_by_currency,
)
from app.services.analytics.periods import GroupBy, _generate_periods
from app.services.analytics.summary import _split_balance_movement
from app.services.exchange_rates import (
    RateResult,
    convert_amount_detailed,
    get_rates_for_periods,
)


async def _account_labels(db: AsyncSession, user_id: int) -> dict[int, str]:
    result = await db.execute(
        select(StorageAccount.id, StorageLocation.name, Currency.code)
        .join(StorageLocation, StorageAccount.storage_location_id == StorageLocation.id)
        .join(Currency, StorageAccount.currency_id == Currency.id)
        .where(StorageAccount.user_id == user_id)
    )
    return {row[0]: f"{row[1]} {row[2]}" for row in result.all()}


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

    Returns the same figures ``get_summary`` reports for that period, alongside
    the snapshots and transactions they were derived from, so a surprising
    number can be traced without reading the database by hand.
    """
    periods = _generate_periods(period, period, group_by)
    if not periods:
        raise ResourceNotFound("period")
    start, end = periods[0]
    prev_end = start - timedelta(days=1)

    converting = convert_to is not None and currency_id is None

    timeline = await get_balance_timeline(db, user_id, [prev_end, end], currency_id)
    prev_accounts = timeline.balances_at(prev_end)
    cur_accounts = timeline.balances_at(end)
    balance_change, opening_capital = _split_balance_movement(
        prev_accounts, cur_accounts
    )

    remeasured = timeline.remeasured_accounts(start, end)
    is_bootstrap = not prev_accounts and bool(cur_accounts)
    is_measured = bool(remeasured & set(prev_accounts))

    rate_map: dict[str, RateResult] = {}
    if converting:
        codes_result = await db.execute(
            select(Currency.code).where(Currency.user_id == user_id)
        )
        rate_cache = await get_rates_for_periods(
            db, list(codes_result.scalars()), [end], to_code=convert_to, user_id=user_id
        )
        rate_map = rate_cache.get(end, {})

    labels = await _account_labels(db, user_id)
    accounts = []
    for account_id in sorted(set(cur_accounts) | set(prev_accounts)):
        opening = prev_accounts.get(account_id)
        closing = cur_accounts.get(account_id)
        accounts.append(
            {
                "account_id": account_id,
                "label": labels.get(account_id, f"Account #{account_id}"),
                "currency": (closing or opening).currency,
                "opening": _snapshot_ref(opening),
                "closing": _snapshot_ref(closing),
                "delta": (
                    closing.amount - opening.amount
                    if opening is not None and closing is not None
                    else Decimal("0")
                ),
                "is_opening_capital": opening is None and closing is not None,
                "remeasured_in_period": account_id in remeasured,
            }
        )

    income_rows = await _income_rows(db, user_id, start, end, currency_id)

    income_by_currency: dict[str, Decimal] = {}
    for row in income_rows:
        income_by_currency[row["currency"]] = (
            income_by_currency.get(row["currency"], Decimal("0")) + row["amount"]
        )

    if converting:
        income, income_missing = convert_amount_detailed(
            income_by_currency, rate_map, convert_to
        )
        profit, profit_missing = convert_amount_detailed(
            balance_change, rate_map, convert_to
        )
        missing = sorted(set(income_missing) | set(profit_missing))
    else:
        income = sum(income_by_currency.values(), Decimal("0"))
        profit = sum(balance_change.values(), Decimal("0"))
        missing = []

    derived_expense = (
        max(Decimal("0"), income - profit) if is_measured else Decimal("0")
    )

    return {
        "period": start.isoformat(),
        "period_start": start,
        "period_end": end,
        "is_bootstrap": is_bootstrap,
        "is_measured": is_measured,
        "currency": convert_to if converting else None,
        "accounts": accounts,
        "income_transactions": income_rows,
        "income_by_currency": income_by_currency,
        "balance_change": balance_change,
        "opening_capital": opening_capital,
        "balances": totals_by_currency(cur_accounts),
        "income": income,
        "profit": profit,
        "derived_expense": derived_expense,
        "conversion_missing": missing,
        "rates": {
            code: {
                "rate": rr.rate,
                "source": rr.source,
                "valid_date": rr.valid_date,
                "status": rr.status,
            }
            for code, rr in rate_map.items()
        },
    }
