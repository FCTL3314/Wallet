from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BalanceSnapshot, Currency, StorageAccount, StorageLocation
from app.services.analytics.periods import GroupBy, _generate_periods


def _latest_snapshot_subquery(user_id: int, before_date: date | None = None):
    """Return a subquery that yields the latest snapshot id per storage account.

    Ranks each account's snapshots by (date DESC, id DESC) and keeps the top row,
    optionally capped at before_date (inclusive). Ranking by date first matters:
    snapshots may be inserted in any order, so a back-filled older snapshot gets a
    higher id than the rows it precedes. Picking by max(id) alone would make that
    back-filled row the "current" balance for every later period.
    """
    conditions = [BalanceSnapshot.user_id == user_id]
    if before_date is not None:
        conditions.append(BalanceSnapshot.date <= before_date)

    ranked = (
        select(
            BalanceSnapshot.id.label("snapshot_id"),
            func.row_number()
            .over(
                partition_by=BalanceSnapshot.storage_account_id,
                order_by=(BalanceSnapshot.date.desc(), BalanceSnapshot.id.desc()),
            )
            .label("rn"),
        )
        .where(*conditions)
        .subquery()
    )
    return (
        select(ranked.c.snapshot_id.label("latest_id"))
        .where(ranked.c.rn == 1)
        .subquery()
    )


@dataclass(frozen=True)
class AccountBalance:
    currency: str
    amount: Decimal
    # Date of the snapshot this balance came from, which is not the date it was
    # carried forward to. Reporting it is what lets a reader see that a period
    # closed on a months-old measurement.
    as_of: date


@dataclass
class BalanceTimeline:
    """Per-account balances at a set of cut-off dates, plus the raw snapshot dates.

    ``per_date`` carries a balance forward: an account keeps its most recent
    snapshot until a newer one appears. ``dates_by_account`` keeps the dates the
    balance was actually re-measured on, which is what tells a period where the
    balance genuinely did not move apart from one where it was simply never
    re-counted.
    """

    per_date: dict[date, dict[int, AccountBalance]] = field(default_factory=dict)
    dates_by_account: dict[int, list[date]] = field(default_factory=dict)

    def balances_at(self, at_date: date) -> dict[int, AccountBalance]:
        return self.per_date.get(at_date, {})

    def remeasured_accounts(self, start: date, end: date) -> set[int]:
        """Accounts with at least one snapshot dated inside [start, end]."""
        return {
            account_id
            for account_id, dates in self.dates_by_account.items()
            if any(start <= d <= end for d in dates)
        }


async def get_balance_timeline(
    db: AsyncSession,
    user_id: int,
    at_dates: list[date],
    currency_id: int | None = None,
) -> BalanceTimeline:
    """Build a BalanceTimeline covering every date in ``at_dates``, in one query.

    Loads the snapshot history once and walks it forward instead of issuing one
    grouped scan per date.
    """
    if not at_dates:
        return BalanceTimeline()

    q = (
        select(
            BalanceSnapshot.storage_account_id,
            BalanceSnapshot.date,
            BalanceSnapshot.amount,
            Currency.code.label("currency"),
        )
        .join(StorageAccount, BalanceSnapshot.storage_account_id == StorageAccount.id)
        .join(Currency, StorageAccount.currency_id == Currency.id)
        .where(
            BalanceSnapshot.user_id == user_id,
            BalanceSnapshot.date <= max(at_dates),
        )
        .order_by(
            BalanceSnapshot.storage_account_id,
            BalanceSnapshot.date,
            BalanceSnapshot.id,
        )
    )
    if currency_id is not None:
        q = q.where(Currency.id == currency_id)
    result = await db.execute(q)

    history: dict[int, list] = {}
    dates_by_account: dict[int, list[date]] = {}
    for row in result.all():
        history.setdefault(row.storage_account_id, []).append(row)
        dates_by_account.setdefault(row.storage_account_id, []).append(row.date)

    # Walk each account's history once, advancing a cursor as the dates increase.
    cursors = dict.fromkeys(history, 0)
    latest: dict[int, object] = {}
    per_date: dict[date, dict[int, AccountBalance]] = {}

    for at_date in sorted(set(at_dates)):
        for account_id, rows in history.items():
            i = cursors[account_id]
            while i < len(rows) and rows[i].date <= at_date:
                latest[account_id] = rows[i]
                i += 1
            cursors[account_id] = i

        per_date[at_date] = {
            account_id: AccountBalance(
                currency=row.currency,
                amount=Decimal(str(row.amount)),
                as_of=row.date,
            )
            for account_id, row in latest.items()
        }

    return BalanceTimeline(per_date=per_date, dates_by_account=dates_by_account)


def totals_by_currency(accounts: dict[int, AccountBalance]) -> dict[str, Decimal]:
    """Collapse per-account balances into per-currency totals."""
    totals: dict[str, Decimal] = {}
    for balance in accounts.values():
        totals[balance.currency] = (
            totals.get(balance.currency, Decimal("0")) + balance.amount
        )
    return totals


async def get_balance_by_storage(
    db: AsyncSession, user_id: int, date_from: date, date_to: date, group_by: GroupBy
) -> list[dict]:
    """For each period, the balance of every account carried forward to the period end.

    An account with no snapshot inside a period keeps the amount from its most
    recent snapshot before it. Accounts with no snapshot at all up to the period
    end are omitted, since their balance is unknown rather than zero.
    """
    periods = _generate_periods(date_from, date_to, group_by)
    if not periods:
        return []

    q = (
        select(
            BalanceSnapshot.storage_account_id,
            BalanceSnapshot.date,
            BalanceSnapshot.amount,
            StorageLocation.name.label("location"),
            Currency.code.label("currency"),
        )
        .join(StorageAccount, BalanceSnapshot.storage_account_id == StorageAccount.id)
        .join(StorageLocation, StorageAccount.storage_location_id == StorageLocation.id)
        .join(Currency, StorageAccount.currency_id == Currency.id)
        .where(
            BalanceSnapshot.user_id == user_id,
            BalanceSnapshot.date <= periods[-1][1],
        )
        .order_by(
            BalanceSnapshot.storage_account_id,
            BalanceSnapshot.date,
            BalanceSnapshot.id,
        )
    )
    result = await db.execute(q)

    history: dict[int, list] = {}
    for row in result.all():
        history.setdefault(row.storage_account_id, []).append(row)

    out: list[dict] = []
    for period_start, period_end in periods:
        accounts: list[dict] = []
        totals: dict[str, Decimal] = {}
        for account_rows in history.values():
            latest = None
            for row in account_rows:
                if row.date > period_end:
                    break
                latest = row
            if latest is None:
                continue
            amount = Decimal(str(latest.amount))
            accounts.append(
                {
                    "name": f"{latest.location} {latest.currency}",
                    "currency": latest.currency,
                    "amount": amount,
                }
            )
            totals[latest.currency] = totals.get(latest.currency, Decimal("0")) + amount
        if not accounts:
            continue
        accounts.sort(key=lambda a: a["name"])
        out.append(
            {
                "period": period_start.isoformat(),
                "accounts": accounts,
                "totals": totals,
            }
        )

    return out


async def get_balance_breakdown(db: AsyncSession, user_id: int) -> list[dict]:
    """
    Return the latest balance snapshot per StorageAccount for the given user up to today.
    """
    today = date.today()
    subq = _latest_snapshot_subquery(user_id, before_date=today)

    q = (
        select(
            StorageAccount.id.label("account_id"),
            StorageLocation.name.label("location_name"),
            Currency.code.label("currency"),
            BalanceSnapshot.date.label("latest_snapshot_date"),
            BalanceSnapshot.amount.label("latest_snapshot_amount"),
        )
        .join(subq, BalanceSnapshot.id == subq.c.latest_id)
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
