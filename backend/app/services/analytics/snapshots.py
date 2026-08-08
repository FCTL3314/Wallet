from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analytics.balance import (
    AccountBalance,
    account_directory,
    account_label,
    get_balance_timeline,
    get_snapshot_dates,
    totals_by_currency,
)
from app.services.analytics.metrics import (
    account_movements,
    pct_change,
    split_balance_movement,
)


async def get_snapshot_timeline(
    db: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
) -> list[dict]:
    """One entry per date the user recorded snapshots on, newest first.

    The movement between two entries is measured with the same
    ``split_balance_movement`` the dashboard uses, so an account tracked for the
    first time shows up as opening capital here too instead of appearing as a
    sudden gain. The two pages disagreed for exactly as long as this was computed
    in the browser.

    Entries outside the requested window are still walked, so the first visible
    entry is compared against the snapshot that really precedes it rather than
    against nothing.
    """
    snapshot_dates = await get_snapshot_dates(db, user_id, date_to=date_to)
    if not snapshot_dates:
        return []

    timeline = await get_balance_timeline(db, user_id, snapshot_dates)
    directory = await account_directory(db, user_id)

    entries: list[dict] = []
    previous: dict[int, AccountBalance] = {}
    previous_totals: dict[str, Decimal] = {}

    for at_date in snapshot_dates:
        balances = timeline.balances_at(at_date)
        totals = totals_by_currency(balances)
        balance_change, opening_capital = split_balance_movement(previous, balances)

        if at_date >= date_from:
            rows = sorted(
                (
                    {
                        "account_id": movement.account_id,
                        "label": account_label(directory, movement.account_id),
                        "currency": movement.currency,
                        "amount": movement.closing.amount,
                        "delta": movement.delta,
                        "is_opening_capital": movement.is_opening_capital,
                        # Only a snapshot dated today is editable here; anything
                        # else is last month's number carried forward.
                        "snapshot_id": (
                            movement.closing.snapshot_id
                            if movement.closing.as_of == at_date
                            else None
                        ),
                        "since": movement.closing.as_of,
                    }
                    for movement in account_movements(previous, balances)
                    if movement.closing is not None
                ),
                key=lambda r: r["label"],
            )

            currencies = sorted(
                (
                    {
                        "code": code,
                        "total": total,
                        "delta": balance_change.get(code),
                        "delta_pct": (
                            pct_change(total, previous_totals[code])
                            if code in previous_totals
                            else None
                        ),
                        "opening_capital": opening_capital.get(code),
                    }
                    for code, total in totals.items()
                ),
                key=lambda c: c["code"],
            )

            entries.append(
                {
                    "date": at_date,
                    "rows": rows,
                    "currencies": currencies,
                    "captured_count": sum(1 for r in rows if r["snapshot_id"]),
                    "locations": sorted(
                        {
                            directory[r["account_id"]].location
                            for r in rows
                            if r["account_id"] in directory
                        }
                    ),
                }
            )

        previous = balances
        previous_totals = totals

    entries.reverse()
    return entries
