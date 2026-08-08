from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BalanceSnapshot, Currency, StorageAccount, StorageLocation
from app.services.analytics.periods import GroupBy, _generate_periods


@dataclass(frozen=True)
class AccountInfo:
    account_id: int
    location: str
    currency: str

    @property
    def label(self) -> str:
        return f"{self.location} {self.currency}"


async def account_directory(db: AsyncSession, user_id: int) -> dict[int, AccountInfo]:
    """Location and currency per storage account.

    One place builds the display label, so an account cannot be called two
    different things depending on which endpoint answered.
    """
    result = await db.execute(
        select(StorageAccount.id, StorageLocation.name, Currency.code)
        .join(StorageLocation, StorageAccount.storage_location_id == StorageLocation.id)
        .join(Currency, StorageAccount.currency_id == Currency.id)
        .where(StorageAccount.user_id == user_id)
    )
    return {
        row[0]: AccountInfo(account_id=row[0], location=row[1], currency=row[2])
        for row in result.all()
    }


def account_label(directory: dict[int, AccountInfo], account_id: int) -> str:
    info = directory.get(account_id)
    return info.label if info else f"Account #{account_id}"


@dataclass(frozen=True)
class AccountBalance:
    currency: str
    amount: Decimal
    # Date of the snapshot this balance came from, which is not the date it was
    # carried forward to. Reporting it is what lets a reader see that a period
    # closed on a months-old measurement.
    as_of: date
    snapshot_id: int


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

    This is the only implementation of "what did each account hold on date X".
    Every balance figure in the app resolves through it, so carrying a stale
    snapshot forward behaves identically everywhere.

    Loads the snapshot history once and walks it forward instead of issuing one
    grouped scan per date. Snapshots are ordered by date before id: they may be
    inserted in any order, so a back-filled older snapshot gets a higher id than
    the rows it precedes, and ordering by id alone would make that back-filled
    row the "current" balance for every later date.
    """
    if not at_dates:
        return BalanceTimeline()

    q = (
        select(
            BalanceSnapshot.id,
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
                snapshot_id=row.id,
            )
            for account_id, row in latest.items()
        }

    return BalanceTimeline(per_date=per_date, dates_by_account=dates_by_account)


async def get_snapshot_dates(
    db: AsyncSession, user_id: int, date_to: date | None = None
) -> list[date]:
    """Every distinct date on which the user recorded at least one snapshot."""
    q = (
        select(BalanceSnapshot.date)
        .where(BalanceSnapshot.user_id == user_id)
        .distinct()
        .order_by(BalanceSnapshot.date)
    )
    if date_to is not None:
        q = q.where(BalanceSnapshot.date <= date_to)
    result = await db.execute(q)
    return list(result.scalars())


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

    period_ends = [end for _, end in periods]
    timeline = await get_balance_timeline(db, user_id, period_ends)
    directory = await account_directory(db, user_id)

    out: list[dict] = []
    for period_start, period_end in periods:
        balances = timeline.balances_at(period_end)
        if not balances:
            continue
        accounts = sorted(
            (
                {
                    "name": account_label(directory, account_id),
                    "currency": balance.currency,
                    "amount": balance.amount,
                }
                for account_id, balance in balances.items()
            ),
            key=lambda a: a["name"],
        )
        out.append(
            {
                "period": period_start.isoformat(),
                "accounts": accounts,
                "totals": totals_by_currency(balances),
            }
        )

    return out


async def get_balance_breakdown(db: AsyncSession, user_id: int) -> dict:
    """The latest known balance of every storage account, as of today.

    The per-currency totals ship with the accounts rather than being re-added by
    each caller, so "what I hold right now" is one number computed in one place.
    """
    today = date.today()
    timeline = await get_balance_timeline(db, user_id, [today])
    directory = await account_directory(db, user_id)
    balances = timeline.balances_at(today)

    accounts = sorted(
        (
            {
                "account_id": account_id,
                "account_label": account_label(directory, account_id),
                "currency": balance.currency,
                "latest_snapshot_date": balance.as_of,
                "latest_snapshot_amount": balance.amount,
            }
            for account_id, balance in balances.items()
        ),
        key=lambda a: a["account_label"],
    )

    return {"accounts": accounts, "totals": totals_by_currency(balances)}
