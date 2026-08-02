from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Currency, Transaction, BalanceSnapshot, ExpenseCategory
from app.services.analytics.periods import GroupBy, _generate_periods
from app.services.analytics.balance import (
    AccountBalance,
    get_balance_timeline,
    totals_by_currency,
)
from app.services.analytics.income import (
    _get_income_per_period,
    _get_income_per_period_by_currency,
)
from app.services.exchange_rates import (
    RateResult,
    convert_amount as _convert_amount,
    convert_amount_detailed,
    get_rates_batch,
    get_rates_for_periods,
)


def _pct(new: Decimal, old: Decimal) -> Decimal | None:
    """Return percentage change from old to new, rounded to 2 dp, or None if old is zero."""
    if old == 0:
        return None
    return ((new - old) / old * 100).quantize(Decimal("0.01"))


def _avg(total: Decimal, count: int) -> Decimal:
    if count == 0:
        return Decimal("0")
    return (total / count).quantize(Decimal("0.01"))


def _split_balance_movement(
    prev_accounts: dict[int, AccountBalance],
    cur_accounts: dict[int, AccountBalance],
) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    """Split a period's balance movement into earned change and opening capital.

    An account seen for the first time in this period brings its whole balance
    with it. That money was not earned during the period — it is capital that
    existed before Wallet started tracking the account — so it is reported
    separately instead of inflating profit. This applies to the very first
    account as much as to a wallet connected years later.
    """
    balance_change: dict[str, Decimal] = {}
    opening_capital: dict[str, Decimal] = {}

    for account_id, balance in cur_accounts.items():
        previous = prev_accounts.get(account_id)
        if previous is None:
            opening_capital[balance.currency] = (
                opening_capital.get(balance.currency, Decimal("0")) + balance.amount
            )
        else:
            delta = balance.amount - previous.amount
            balance_change[balance.currency] = (
                balance_change.get(balance.currency, Decimal("0")) + delta
            )

    return balance_change, opening_capital


async def _build_rate_coverage(
    db: AsyncSession, user_id: int, base_currency: str = "USD"
) -> dict:
    """Build rate coverage info for all currencies owned by the user."""

    result = await db.execute(select(Currency.code).where(Currency.user_id == user_id))
    all_codes = list(result.scalars())

    # Exclude base currency from coverage check
    non_base_codes = [c for c in all_codes if c != base_currency]

    if not non_base_codes:
        return {
            "base_currency": base_currency,
            "currencies": {},
            "conversion_available": True,
        }

    rate_map = await get_rates_batch(
        db, non_base_codes, to_code=base_currency, user_id=user_id
    )

    currencies: dict[str, dict] = {}
    all_ok = True
    for code in non_base_codes:
        rr = rate_map.get(code)
        if rr is None:
            currencies[code] = {
                "status": "missing",
                "valid_date": None,
                "source": "none",
                "rate": None,
            }
            all_ok = False
        else:
            currencies[code] = {
                "status": rr.status,
                "valid_date": rr.valid_date,
                "source": rr.source,
                "rate": str(rr.rate) if rr.rate is not None else None,
            }
            if rr.status != "ok":
                all_ok = False

    return {
        "base_currency": base_currency,
        "currencies": currencies,
        "conversion_available": all_ok,
    }


async def get_summary(
    db: AsyncSession,
    user_id: int,
    date_from: date,
    date_to: date,
    group_by: GroupBy,
    currency_id: int | None = None,
    convert_to: str | None = None,
) -> dict:
    """
    Excel-model summary: profit = balance_change, derived_expense = income - profit.
    Generates one row per calendar period in the requested range.

    Profit is only reported for periods where it can actually be measured: an
    already-tracked account has to have been re-counted inside the period. A
    period that merely carries the previous balance forward is marked
    ``is_measured: false`` and contributes to no average, because "the balance
    did not move" and "nobody wrote the balance down" are indistinguishable
    from the snapshots alone.

    When ``convert_to`` is set (e.g. "USD"), all monetary values are converted
    to that currency using exchange rates. Each period entry gets an extra
    ``converted_balance`` field with the total converted balance.

    Returns ``{"periods": [...], "stats": {...}, "rate_coverage": {...}}``.
    """
    periods = _generate_periods(date_from, date_to, group_by)
    if not periods:
        return {"periods": [], "stats": None, "rate_coverage": None}

    # Periods are whole calendar units, so the income window has to span the
    # generated periods rather than the raw request. Asking for "15 Mar - 2 Aug"
    # renders a full March row whose balance delta covers the whole month;
    # counting income only from the 15th would understate that row's expense.
    range_start, range_end = periods[0][0], periods[-1][1]

    converting = convert_to is not None and currency_id is None

    # Pre-fetch currency codes for conversion mode
    all_codes: list[str] = []
    if converting:
        all_codes_result = await db.execute(
            select(Currency.code).where(Currency.user_id == user_id)
        )
        all_codes = list(all_codes_result.scalars())

    # Get income data
    if converting:
        income_map_by_cur = await _get_income_per_period_by_currency(
            db, user_id, range_start, range_end, group_by
        )
        income_map: dict[str, Decimal] = {}
    else:
        income_map_by_cur = None
        income_map = await _get_income_per_period(
            db, user_id, range_start, range_end, group_by, currency_id
        )

    # Balances at every period end, plus the day before the first period, in one query
    prev_end = range_start - timedelta(days=1)
    balance_dates = [prev_end] + [end for _, end in periods]
    timeline = await get_balance_timeline(db, user_id, balance_dates, currency_id)

    prev_accounts = timeline.balances_at(prev_end)

    # Save initial balances for balance_growth stat (before any period mutations)
    initial_balances = totals_by_currency(prev_accounts)

    # Pre-fetch rates for all period-ends in 2 queries (avoid N+1)
    rate_cache: dict[date, dict[str, RateResult]] = {}
    if converting:
        period_ends_list = [end for _, end in periods]
        rate_cache = await get_rates_for_periods(
            db, all_codes, period_ends_list, to_code=convert_to, user_id=user_id
        )

    summary = []
    total_income = Decimal("0")
    income_count = 0

    # Averages share one denominator: the periods where income, profit and the
    # expense derived from them are all meaningful at once. Mixing denominators
    # (income averaged over earning periods, profit over active ones) produces
    # three cards that cannot be reconciled with each other.
    accountable_income = Decimal("0")
    accountable_profit = Decimal("0")
    accountable_expense = Decimal("0")
    accountable_count = 0

    # Data collected for growth stats
    income_active_periods: list[dict] = []  # periods where income > 0
    profit_active_periods: list[dict] = []  # measured periods with any activity
    last_cur_balances: dict[str, Decimal] = {}

    for period_start, period_end in periods:
        period_key = period_start.isoformat()

        # Fetch exchange rates at period_end for accurate historical conversion
        rate_map: dict[str, RateResult] = (
            rate_cache.get(period_end, {}) if converting else {}
        )

        # Compute income for this period
        if converting:
            income_by_cur = income_map_by_cur.get(period_key, {})
            income = _convert_amount(income_by_cur, rate_map, convert_to)
        else:
            income = income_map.get(period_key, Decimal("0"))

        cur_accounts = timeline.balances_at(period_end)
        cur_balances = totals_by_currency(cur_accounts)

        balance_change, opening_capital = _split_balance_movement(
            prev_accounts, cur_accounts
        )

        if converting:
            profit = _convert_amount(balance_change, rate_map, convert_to)
        else:
            profit = sum(balance_change.values(), Decimal("0"))

        # A bootstrap period is one that opens the very first tracked balance.
        # Any first snapshot qualifies, including a net-negative one — testing the
        # summed total would both miss debt-only openings and add up unlike currencies.
        is_bootstrap = not prev_accounts and bool(cur_accounts)

        # Profit is only measurable when an already-tracked account was re-counted
        # inside the period. Without that the balance is merely carried forward, and
        # reading its flat line as "earned nothing, so spent it all" is what made an
        # unfinished month look like a month of pure expense.
        is_measured = bool(
            timeline.remeasured_accounts(period_start, period_end) & set(prev_accounts)
        )
        derived_expense = (
            max(Decimal("0"), income - profit) if is_measured else Decimal("0")
        )

        # Income is money actually received and is reported in every period, but
        # only measured periods feed the averages and growth stats.
        total_income += income
        if income > 0:
            income_count += 1
            income_active_periods.append(
                {"period": period_key, "income": income, "profit": profit}
            )
        if is_measured:
            accountable_income += income
            accountable_profit += profit
            accountable_expense += derived_expense
            accountable_count += 1
            if income > 0 or profit != 0:
                profit_active_periods.append(
                    {"period": period_key, "income": income, "profit": profit}
                )

        entry = {
            "period": period_key,
            "income": income,
            "profit": profit,
            "derived_expense": derived_expense,
            "avg_income": _avg(accountable_income, accountable_count),
            "avg_profit": _avg(accountable_profit, accountable_count),
            "avg_expense": _avg(accountable_expense, accountable_count),
            "balances": cur_balances,
            "balance_change": balance_change,
            "opening_capital": opening_capital,
            "is_bootstrap": is_bootstrap,
            "is_measured": is_measured,
        }

        if converting:
            converted_balance, missing = convert_amount_detailed(
                cur_balances, rate_map, convert_to
            )
            entry["converted_balance"] = converted_balance
            entry["conversion_missing"] = missing

        summary.append(entry)

        prev_accounts = cur_accounts
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

    balance_growth_converted = None
    if converting:
        last_rate_map = rate_cache.get(periods[-1][1], {})
        init_converted = _convert_amount(initial_balances, last_rate_map, convert_to)
        final_converted = _convert_amount(last_cur_balances, last_rate_map, convert_to)
        balance_growth_converted = {
            "delta": final_converted - init_converted,
            "pct": _pct(final_converted, init_converted),
            "currency": convert_to,
        }

    stats = {
        "income_growth": income_growth,
        "profit_growth": profit_growth,
        "balance_growth": {
            "delta": balance_growth_delta,
            "pct": balance_growth_pct,
        },
        "balance_growth_converted": balance_growth_converted,
        "total_income": total_income,
        "total_profit": accountable_profit,
        "total_expense": accountable_expense,
        "avg_income": _avg(accountable_income, accountable_count),
        "avg_profit": _avg(accountable_profit, accountable_count),
        "avg_expense": _avg(accountable_expense, accountable_count),
        "accountable_period_count": accountable_count,
        "income_period_count": income_count,
    }

    # --- Compute rate_coverage ---
    rate_coverage = (
        await _build_rate_coverage(db, user_id, base_currency=convert_to)
        if converting
        else None
    )

    return {"periods": summary, "stats": stats, "rate_coverage": rate_coverage}


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
