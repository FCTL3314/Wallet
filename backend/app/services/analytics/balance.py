from datetime import date
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BalanceSnapshot, Currency, StorageAccount, StorageLocation
from app.services.analytics.periods import GroupBy


async def _get_balance_at_date(
    db: AsyncSession, user_id: int, at_date: date, currency_id: int | None = None
) -> dict:
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
        .join(
            subq,
            and_(
                BalanceSnapshot.storage_account_id == subq.c.storage_account_id,
                BalanceSnapshot.date == subq.c.max_date,
            ),
        )
        .join(StorageAccount, BalanceSnapshot.storage_account_id == StorageAccount.id)
        .join(Currency, StorageAccount.currency_id == Currency.id)
        .where(BalanceSnapshot.user_id == user_id)
        .group_by(Currency.code)
    )
    if currency_id is not None:
        q = q.where(Currency.id == currency_id)
    result = await db.execute(q)
    return {row.code: Decimal(str(row.total)) for row in result.all()}


async def get_balance_by_storage(
    db: AsyncSession, user_id: int, date_from: date, date_to: date, group_by: GroupBy
) -> list[dict]:
    """For each period, get balance per storage account from the latest snapshot in that period."""
    period = (func.date_trunc(group_by.value, BalanceSnapshot.date)).label("period")

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
        .join(
            subq,
            and_(
                BalanceSnapshot.storage_account_id == subq.c.storage_account_id,
                BalanceSnapshot.date == subq.c.max_date,
            ),
        )
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
        grouped[p]["accounts"].append(
            {"name": acc_name, "currency": row.currency, "amount": amount}
        )
        grouped[p]["totals"][row.currency] = (
            grouped[p]["totals"].get(row.currency, Decimal("0")) + amount
        )

    return list(grouped.values())


async def get_balance_breakdown(db: AsyncSession, user_id: int) -> list[dict]:
    """
    Return the latest balance snapshot per StorageAccount for the given user up to today.
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
        .join(
            subq,
            and_(
                BalanceSnapshot.storage_account_id == subq.c.storage_account_id,
                BalanceSnapshot.date == subq.c.max_date,
            ),
        )
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
