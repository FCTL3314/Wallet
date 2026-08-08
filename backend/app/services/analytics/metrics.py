from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.services.analytics.balance import AccountBalance, totals_by_currency
from app.services.analytics.money import MoneyConverter


@dataclass(frozen=True)
class AccountMovement:
    """What one account did over one period."""

    account_id: int
    currency: str
    opening: AccountBalance | None
    closing: AccountBalance | None
    delta: Decimal
    is_opening_capital: bool


def account_movements(
    prev_accounts: dict[int, AccountBalance],
    cur_accounts: dict[int, AccountBalance],
) -> list[AccountMovement]:
    """Classify every account's movement over a period.

    An account seen for the first time in this period brings its whole balance
    with it. That money was not earned during the period — it is capital that
    existed before Wallet started tracking the account — so it is flagged as
    opening capital instead of counting as movement. This applies to the very
    first account as much as to a wallet connected years later.

    This is the only place that rule is written down; both the per-currency
    rollup and the per-account breakdown shown to users read it from here.
    """
    movements: list[AccountMovement] = []
    for account_id in sorted(set(prev_accounts) | set(cur_accounts)):
        opening = prev_accounts.get(account_id)
        closing = cur_accounts.get(account_id)
        reference = closing or opening
        if reference is None:
            continue

        is_opening_capital = opening is None and closing is not None
        if opening is not None and closing is not None:
            delta = closing.amount - opening.amount
        else:
            delta = Decimal("0")

        movements.append(
            AccountMovement(
                account_id=account_id,
                currency=reference.currency,
                opening=opening,
                closing=closing,
                delta=delta,
                is_opening_capital=is_opening_capital,
            )
        )
    return movements


def split_balance_movement(
    prev_accounts: dict[int, AccountBalance],
    cur_accounts: dict[int, AccountBalance],
) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    """Roll account movements up per currency into earned change and opening capital."""
    balance_change: dict[str, Decimal] = {}
    opening_capital: dict[str, Decimal] = {}

    for movement in account_movements(prev_accounts, cur_accounts):
        # An account with no closing balance has no measurable position at the
        # period end, so it contributes to neither bucket.
        if movement.closing is None:
            continue
        if movement.is_opening_capital:
            bucket, amount = opening_capital, movement.closing.amount
        else:
            bucket, amount = balance_change, movement.delta
        bucket[movement.currency] = bucket.get(movement.currency, Decimal("0")) + amount

    return balance_change, opening_capital


@dataclass(frozen=True)
class PeriodMetrics:
    """Every derived figure Wallet reports about one period.

    This is the only place profit, expense and measurability are decided. Any
    endpoint that shows those numbers builds one of these rather than repeating
    the arithmetic, so a row and its explanation cannot disagree.
    """

    period_start: date
    period_end: date
    income: Decimal
    profit: Decimal
    derived_expense: Decimal
    balances: dict[str, Decimal]
    balance_change: dict[str, Decimal]
    opening_capital: dict[str, Decimal]
    income_by_currency: dict[str, Decimal]
    is_bootstrap: bool
    is_measured: bool
    converted_balance: Decimal | None
    conversion_missing: list[str]

    @property
    def period(self) -> str:
        return self.period_start.isoformat()

    def as_row(self, include_converted: bool) -> dict:
        row = {
            "period": self.period,
            "income": self.income,
            "profit": self.profit,
            "derived_expense": self.derived_expense,
            "balances": self.balances,
            "balance_change": self.balance_change,
            "opening_capital": self.opening_capital,
            "is_bootstrap": self.is_bootstrap,
            "is_measured": self.is_measured,
        }
        if include_converted:
            row["converted_balance"] = self.converted_balance
            row["conversion_missing"] = self.conversion_missing
        return row


def compute_period_metrics(
    period_start: date,
    period_end: date,
    prev_accounts: dict[int, AccountBalance],
    cur_accounts: dict[int, AccountBalance],
    income_by_currency: dict[str, Decimal],
    remeasured_accounts: set[int],
    converter: MoneyConverter,
) -> PeriodMetrics:
    """Turn one period's raw balances and income into the figures Wallet reports.

    Profit is the change in what the user holds, not income minus receipts, and
    it is only reported when an already-tracked account was actually re-counted
    inside the period. Without that the balance is merely carried forward, and
    reading its flat line as "earned nothing, so spent it all" is what made an
    unfinished month look like a month of pure expense.
    """
    balances = totals_by_currency(cur_accounts)
    balance_change, opening_capital = split_balance_movement(
        prev_accounts, cur_accounts
    )

    income_result = converter.collapse_detailed(income_by_currency, period_end)
    profit_result = converter.collapse_detailed(balance_change, period_end)

    # A bootstrap period is one that opens the very first tracked balance. Any
    # first snapshot qualifies, including a net-negative one — testing the summed
    # total would both miss debt-only openings and add up unlike currencies.
    is_bootstrap = not prev_accounts and bool(cur_accounts)
    is_measured = bool(remeasured_accounts & set(prev_accounts))

    derived_expense = (
        max(Decimal("0"), income_result.value - profit_result.value)
        if is_measured
        else Decimal("0")
    )

    converted_balance: Decimal | None = None
    conversion_missing: list[str] = []
    if converter.converting:
        balance_result = converter.collapse_detailed(balances, period_end)
        converted_balance = balance_result.value
        conversion_missing = sorted(
            set(balance_result.missing)
            | set(income_result.missing)
            | set(profit_result.missing)
        )

    return PeriodMetrics(
        period_start=period_start,
        period_end=period_end,
        income=income_result.value,
        profit=profit_result.value,
        derived_expense=derived_expense,
        balances=balances,
        balance_change=balance_change,
        opening_capital=opening_capital,
        income_by_currency=income_by_currency,
        is_bootstrap=is_bootstrap,
        is_measured=is_measured,
        converted_balance=converted_balance,
        conversion_missing=conversion_missing,
    )


def pct_change(new: Decimal, old: Decimal) -> Decimal | None:
    """Percentage change from old to new, or None when the base is zero."""
    if old == 0:
        return None
    return ((new - old) / old * 100).quantize(Decimal("0.01"))


def average(total: Decimal, count: int) -> Decimal:
    if count == 0:
        return Decimal("0")
    return (total / count).quantize(Decimal("0.01"))


@dataclass
class MetricAccumulator:
    """Running totals across periods, and the rule for what may feed an average.

    Averages share one denominator: the periods where income, profit and the
    expense derived from them are all meaningful at once. Mixing denominators
    (income averaged over earning periods, profit over measured ones) produces
    cards that cannot be reconciled with each other.
    """

    total_income: Decimal = Decimal("0")
    income_count: int = 0
    accountable_income: Decimal = Decimal("0")
    accountable_profit: Decimal = Decimal("0")
    accountable_expense: Decimal = Decimal("0")
    accountable_count: int = 0
    income_active_periods: list[dict] = field(default_factory=list)
    profit_active_periods: list[dict] = field(default_factory=list)

    def add(self, metrics: PeriodMetrics) -> None:
        # Income is money actually received and is reported in every period, but
        # only measured periods feed the averages and growth stats.
        self.total_income += metrics.income
        if metrics.income > 0:
            self.income_count += 1
            self.income_active_periods.append(
                {
                    "period": metrics.period,
                    "income": metrics.income,
                    "profit": metrics.profit,
                }
            )
        if not metrics.is_measured:
            return

        self.accountable_income += metrics.income
        self.accountable_profit += metrics.profit
        self.accountable_expense += metrics.derived_expense
        self.accountable_count += 1
        if metrics.income > 0 or metrics.profit != 0:
            self.profit_active_periods.append(
                {
                    "period": metrics.period,
                    "income": metrics.income,
                    "profit": metrics.profit,
                }
            )

    @property
    def avg_income(self) -> Decimal:
        return average(self.accountable_income, self.accountable_count)

    @property
    def avg_profit(self) -> Decimal:
        return average(self.accountable_profit, self.accountable_count)

    @property
    def avg_expense(self) -> Decimal:
        return average(self.accountable_expense, self.accountable_count)


def growth_stat(active_periods: list[dict], key: str) -> dict | None:
    """First-to-last change across the periods where ``key`` was meaningful."""
    if len(active_periods) < 2:
        return None
    first, last = active_periods[0], active_periods[-1]
    return {
        "delta": last[key] - first[key],
        "pct": pct_change(last[key], first[key]),
        "from_period": first["period"],
        "to_period": last["period"],
    }
