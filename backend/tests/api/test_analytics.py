from datetime import date
from decimal import Decimal

from app.models import BalanceSnapshot, Transaction
from app.models.transaction import TransactionType


async def _seed_transactions(db_session, user, ref_data):
    """Create a set of income transactions for analytics tests."""
    account = ref_data["account"]
    currency = ref_data["currency"]
    income_source = ref_data["income_source"]

    txns = [
        Transaction(
            user_id=user.id,
            type=TransactionType.income,
            date=date(2025, 1, 15),
            amount=Decimal("3000.00"),
            currency_id=currency.id,
            storage_account_id=account.id,
            income_source_id=income_source.id,
        ),
        Transaction(
            user_id=user.id,
            type=TransactionType.income,
            date=date(2025, 2, 15),
            amount=Decimal("3200.00"),
            currency_id=currency.id,
            storage_account_id=account.id,
            income_source_id=income_source.id,
        ),
    ]
    for t in txns:
        db_session.add(t)
    await db_session.flush()
    return txns


async def test_summary_empty_period(auth_client, test_user, ref_data):
    """Summary for a period with no data returns one entry per calendar month, all zeroed."""
    resp = await auth_client.get(
        "/api/analytics/summary",
        params={
            "date_from": "2099-01-01",
            "date_to": "2099-03-31",
            "group_by": "month",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    periods = data["periods"]
    assert len(periods) == 3
    assert all(float(row["income"]) == 0.0 for row in periods)
    assert all(float(row["profit"]) == 0.0 for row in periods)


async def test_summary_with_transactions(auth_client, test_user, ref_data, db_session):
    account = ref_data["account"]
    currency = ref_data["currency"]
    income_source = ref_data["income_source"]

    db_session.add_all(
        [
            Transaction(
                user_id=test_user.id,
                type=TransactionType.income,
                date=date(2025, 1, 15),
                amount=Decimal("3000.00"),
                currency_id=currency.id,
                storage_account_id=account.id,
                income_source_id=income_source.id,
            ),
            Transaction(
                user_id=test_user.id,
                type=TransactionType.income,
                date=date(2025, 2, 15),
                amount=Decimal("3200.00"),
                currency_id=currency.id,
                storage_account_id=account.id,
                income_source_id=income_source.id,
            ),
        ]
    )
    db_session.add_all(
        [
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=account.id,
                date=date(2025, 1, 31),
                amount=Decimal("2500.00"),
            ),
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=account.id,
                date=date(2025, 2, 28),
                amount=Decimal("5100.00"),
            ),
        ]
    )
    await db_session.flush()

    resp = await auth_client.get(
        "/api/analytics/summary",
        params={
            "date_from": "2025-01-01",
            "date_to": "2025-02-28",
            "group_by": "month",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    periods = data["periods"]
    assert len(periods) == 2

    jan = periods[0]
    assert float(jan["income"]) == 3000.0
    # The opening snapshot is capital brought in, not profit earned in January.
    assert float(jan["profit"]) == 0.0
    assert float(jan["opening_capital"]["USD"]) == 2500.0
    assert jan["is_bootstrap"] is True
    assert jan["is_measured"] is False
    assert float(jan["derived_expense"]) == 0.0

    feb = periods[1]
    assert float(feb["income"]) == 3200.0
    assert float(feb["profit"]) == 2600.0
    assert feb["is_bootstrap"] is False
    assert feb["is_measured"] is True
    assert float(feb["derived_expense"]) == 600.0

    # February is the only accountable period, so every average is its own figure.
    assert float(feb["avg_income"]) == 3200.0
    assert float(feb["avg_profit"]) == 2600.0
    assert float(feb["avg_expense"]) == 600.0
    assert data["stats"]["accountable_period_count"] == 1


async def test_summary_income_only_no_snapshots(
    auth_client, test_user, ref_data, db_session
):
    """Income with no snapshots: profit is unmeasured, so no expense is derived."""
    account = ref_data["account"]
    currency = ref_data["currency"]
    income_source = ref_data["income_source"]

    db_session.add(
        Transaction(
            user_id=test_user.id,
            type=TransactionType.income,
            date=date(2025, 3, 10),
            amount=Decimal("4000.00"),
            currency_id=currency.id,
            storage_account_id=account.id,
            income_source_id=income_source.id,
        )
    )
    await db_session.flush()

    resp = await auth_client.get(
        "/api/analytics/summary",
        params={
            "date_from": "2025-03-01",
            "date_to": "2025-03-31",
            "group_by": "month",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    periods = data["periods"]
    assert len(periods) == 1
    row = periods[0]
    assert float(row["income"]) == 4000.0
    assert float(row["profit"]) == 0.0
    assert row["is_bootstrap"] is False
    # Nothing was ever counted, so "spent it all" is not a conclusion to draw.
    assert row["is_measured"] is False
    assert float(row["derived_expense"]) == 0.0
    assert data["stats"]["accountable_period_count"] == 0


async def test_summary_with_balance_snapshots(
    auth_client, test_user, ref_data, db_session
):
    await _seed_transactions(db_session, test_user, ref_data)

    snap = BalanceSnapshot(
        user_id=test_user.id,
        storage_account_id=ref_data["account"].id,
        date=date(2025, 1, 31),
        amount=Decimal("10000.00"),
    )
    db_session.add(snap)
    await db_session.flush()

    resp = await auth_client.get(
        "/api/analytics/summary",
        params={
            "date_from": "2025-01-01",
            "date_to": "2025-01-31",
            "group_by": "month",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    periods = data["periods"]
    assert len(periods) == 1
    assert "balances" in periods[0]
    assert float(periods[0]["balances"]["USD"]) == 10000.0


async def test_income_by_source(auth_client, test_user, ref_data, db_session):
    await _seed_transactions(db_session, test_user, ref_data)

    resp = await auth_client.get(
        "/api/analytics/income-by-source",
        params={
            "date_from": "2025-01-01",
            "date_to": "2025-02-28",
            "group_by": "month",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["periods"]) == 2
    # Each period should have the "Salary" source
    for period in data["periods"]:
        assert "Salary" in period["sources"]
    # The range totals are a rollup of the same cells, not a separate query.
    assert float(data["total"]) == sum(float(p["total"]) for p in data["periods"])
    assert set(data["totals"]) == {"Salary"}


async def test_balance_by_storage(auth_client, test_user, ref_data, db_session):
    snap = BalanceSnapshot(
        user_id=test_user.id,
        storage_account_id=ref_data["account"].id,
        date=date(2025, 1, 31),
        amount=Decimal("5000.00"),
    )
    db_session.add(snap)
    await db_session.flush()

    resp = await auth_client.get(
        "/api/analytics/balance-by-storage",
        params={
            "date_from": "2025-01-01",
            "date_to": "2025-01-31",
            "group_by": "month",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    period = data[0]
    assert len(period["accounts"]) == 1
    assert period["accounts"][0]["currency"] == "USD"
    assert float(period["accounts"][0]["amount"]) == 5000.0


async def test_balance_by_storage_carries_unchanged_accounts_forward(
    auth_client, test_user, ref_data, db_session
):
    from app.models import Currency, StorageAccount

    eur = Currency(code="EUR", symbol="€", user_id=test_user.id)
    db_session.add(eur)
    await db_session.flush()

    eur_account = StorageAccount(
        storage_location_id=ref_data["location"].id,
        currency_id=eur.id,
        user_id=test_user.id,
    )
    db_session.add(eur_account)
    await db_session.flush()

    db_session.add_all(
        [
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=ref_data["account"].id,
                date=date(2025, 1, 31),
                amount=Decimal("7060.00"),
            ),
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=eur_account.id,
                date=date(2025, 1, 31),
                amount=Decimal("2000.00"),
            ),
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=eur_account.id,
                date=date(2025, 2, 28),
                amount=Decimal("2058.44"),
            ),
        ]
    )
    await db_session.flush()

    resp = await auth_client.get(
        "/api/analytics/balance-by-storage",
        params={
            "date_from": "2025-01-01",
            "date_to": "2025-02-28",
            "group_by": "month",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    february = data[1]
    assert february["period"] == "2025-02-01"
    assert len(february["accounts"]) == 2
    assert float(february["totals"]["USD"]) == 7060.0
    assert float(february["totals"]["EUR"]) == 2058.44


async def test_expense_template(auth_client, test_user, ref_data, db_session):
    from app.models import ExpenseCategory

    tax_cat = ExpenseCategory(
        name="Tax",
        budgeted_amount=Decimal("200.00"),
        tags=["tax"],
        user_id=test_user.id,
    )
    db_session.add(tax_cat)
    await db_session.flush()

    resp = await auth_client.get("/api/analytics/expense-template")
    assert resp.status_code == 200
    data = resp.json()

    # ref_data has Food=500, plus Tax=200
    assert float(data["total"]) == 700.0
    assert float(data["without_tax"]) == 500.0
    assert len(data["items"]) == 2


async def test_balance_uses_latest_date_not_latest_insert(
    auth_client, test_user, ref_data, db_session
):
    """A back-filled older snapshot must not become the current balance.

    Snapshots can be entered in any order, so the row inserted last is not the
    row with the latest date. Ranking by id alone made one forgotten month
    override the true balance for every period after it.
    """
    account = ref_data["account"]

    db_session.add(
        BalanceSnapshot(
            user_id=test_user.id,
            storage_account_id=account.id,
            date=date(2025, 6, 30),
            amount=Decimal("5000.00"),
        )
    )
    await db_session.flush()

    # Back-fill an earlier month afterwards, so it gets the higher id.
    db_session.add(
        BalanceSnapshot(
            user_id=test_user.id,
            storage_account_id=account.id,
            date=date(2025, 1, 31),
            amount=Decimal("100.00"),
        )
    )
    await db_session.flush()

    resp = await auth_client.get("/api/analytics/balance-breakdown")
    assert resp.status_code == 200
    body = resp.json()
    rows = body["accounts"]
    assert len(rows) == 1
    assert rows[0]["latest_snapshot_date"] == "2025-06-30"
    assert float(rows[0]["latest_snapshot_amount"]) == 5000.0
    assert body["totals"] == {"USD": 5000.0}


async def test_summary_keeps_income_in_bootstrap_period(
    auth_client, test_user, ref_data, db_session
):
    """Opening-balance periods must still report the income received in them."""
    account = ref_data["account"]

    db_session.add(
        Transaction(
            user_id=test_user.id,
            type=TransactionType.income,
            date=date(2025, 1, 10),
            amount=Decimal("2500.00"),
            currency_id=ref_data["currency"].id,
            storage_account_id=account.id,
            income_source_id=ref_data["income_source"].id,
        )
    )
    db_session.add(
        BalanceSnapshot(
            user_id=test_user.id,
            storage_account_id=account.id,
            date=date(2025, 1, 31),
            amount=Decimal("9000.00"),
        )
    )
    await db_session.flush()

    resp = await auth_client.get(
        "/api/analytics/summary",
        params={
            "date_from": "2025-01-01",
            "date_to": "2025-01-31",
            "group_by": "month",
        },
    )
    assert resp.status_code == 200
    data = resp.json()

    row = data["periods"][0]
    assert row["is_bootstrap"] is True
    # Income is real money received and is reported...
    assert float(row["income"]) == 2500.0
    # ...while the opening balance is not booked as profit.
    assert float(data["stats"]["total_income"]) == 2500.0
    assert float(data["stats"]["total_profit"]) == 0.0


async def _account_at_new_location(
    db_session, user, currency_id: int, location_name: str
):
    """Create another storage account for an existing currency, at a new location."""
    from app.models import StorageAccount, StorageLocation

    location = StorageLocation(name=location_name, user_id=user.id)
    db_session.add(location)
    await db_session.flush()
    account = StorageAccount(
        storage_location_id=location.id, currency_id=currency_id, user_id=user.id
    )
    db_session.add(account)
    await db_session.flush()
    return account


async def _new_currency_account(db_session, user, code: str, location_name: str):
    """Create a storage account in a brand new currency and location."""
    from app.models import Currency

    currency = Currency(code=code, symbol=code[0], user_id=user.id)
    db_session.add(currency)
    await db_session.flush()
    account = await _account_at_new_location(
        db_session, user, currency.id, location_name
    )
    return account, currency


async def test_summary_new_account_opening_balance_is_not_profit(
    auth_client, test_user, ref_data, db_session
):
    """Connecting an account that already held money must not book it as profit."""
    account = ref_data["account"]
    db_session.add_all(
        [
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=account.id,
                date=date(2025, 1, 31),
                amount=Decimal("1000.00"),
            ),
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=account.id,
                date=date(2025, 2, 28),
                amount=Decimal("1200.00"),
            ),
        ]
    )
    # A second account joins in February carrying a balance it has held for years.
    second = await _account_at_new_location(
        db_session, test_user, ref_data["currency"].id, "Broker"
    )
    db_session.add(
        BalanceSnapshot(
            user_id=test_user.id,
            storage_account_id=second.id,
            date=date(2025, 2, 28),
            amount=Decimal("500000.00"),
        )
    )
    await db_session.flush()

    resp = await auth_client.get(
        "/api/analytics/summary",
        params={
            "date_from": "2025-01-01",
            "date_to": "2025-02-28",
            "group_by": "month",
        },
    )
    assert resp.status_code == 200
    feb = resp.json()["periods"][1]

    # Only the account that already existed contributes to profit.
    assert float(feb["profit"]) == 200.0
    assert float(feb["balance_change"]["USD"]) == 200.0
    assert float(feb["opening_capital"]["USD"]) == 500000.0
    # The money is still part of what the user holds, just not part of what they earned.
    assert float(feb["balances"]["USD"]) == 501200.0


async def test_summary_unmeasured_period_excluded_from_averages(
    auth_client, test_user, ref_data, db_session
):
    """A month with no fresh snapshot must not drag the averages toward zero."""
    account = ref_data["account"]
    db_session.add_all(
        [
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=account.id,
                date=date(2025, 1, 31),
                amount=Decimal("1000.00"),
            ),
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=account.id,
                date=date(2025, 2, 28),
                amount=Decimal("3000.00"),
            ),
        ]
    )
    # March has income but was never snapshotted — the balance only carries forward.
    db_session.add(
        Transaction(
            user_id=test_user.id,
            type=TransactionType.income,
            date=date(2025, 3, 10),
            amount=Decimal("9999.00"),
            currency_id=ref_data["currency"].id,
            storage_account_id=account.id,
            income_source_id=ref_data["income_source"].id,
        )
    )
    await db_session.flush()

    resp = await auth_client.get(
        "/api/analytics/summary",
        params={
            "date_from": "2025-01-01",
            "date_to": "2025-03-31",
            "group_by": "month",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    march = data["periods"][2]

    assert march["is_measured"] is False
    assert float(march["derived_expense"]) == 0.0
    # Only February is accountable, so its profit is the average, undiluted by March.
    assert data["stats"]["accountable_period_count"] == 1
    assert float(march["avg_profit"]) == 2000.0
    # Income received in March is still reported and still counted in the total.
    assert float(march["income"]) == 9999.0
    assert float(data["stats"]["total_income"]) == 9999.0


async def test_summary_averages_share_one_denominator(
    auth_client, test_user, ref_data, db_session
):
    """avg_income - avg_profit must reconcile with avg_expense."""
    account = ref_data["account"]
    amounts = [
        ("2025-01-31", "1000.00"),
        ("2025-02-28", "1500.00"),
        ("2025-03-31", "1800.00"),
    ]
    for snap_date, amount in amounts:
        db_session.add(
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=account.id,
                date=date.fromisoformat(snap_date),
                amount=Decimal(amount),
            )
        )
    # Income lands in February only; March is snapshotted but earns nothing.
    db_session.add(
        Transaction(
            user_id=test_user.id,
            type=TransactionType.income,
            date=date(2025, 2, 15),
            amount=Decimal("2000.00"),
            currency_id=ref_data["currency"].id,
            storage_account_id=account.id,
            income_source_id=ref_data["income_source"].id,
        )
    )
    await db_session.flush()

    resp = await auth_client.get(
        "/api/analytics/summary",
        params={
            "date_from": "2025-01-01",
            "date_to": "2025-03-31",
            "group_by": "month",
        },
    )
    assert resp.status_code == 200
    stats = resp.json()["stats"]

    # February and March are accountable: income 2000/0, profit 500/300.
    assert stats["accountable_period_count"] == 2
    assert float(stats["avg_income"]) == 1000.0
    assert float(stats["avg_profit"]) == 400.0
    # Expense is averaged from the per-period figures, not from the two averages.
    assert float(stats["avg_expense"]) == 750.0


async def test_summary_income_window_covers_whole_first_period(
    auth_client, test_user, ref_data, db_session
):
    """A mid-month date_from still renders a whole month, so it must count the whole month."""
    db_session.add(
        Transaction(
            user_id=test_user.id,
            type=TransactionType.income,
            date=date(2025, 3, 5),
            amount=Decimal("700.00"),
            currency_id=ref_data["currency"].id,
            storage_account_id=ref_data["account"].id,
            income_source_id=ref_data["income_source"].id,
        )
    )
    await db_session.flush()

    resp = await auth_client.get(
        "/api/analytics/summary",
        params={
            "date_from": "2025-03-20",
            "date_to": "2025-03-31",
            "group_by": "month",
        },
    )
    assert resp.status_code == 200
    periods = resp.json()["periods"]
    assert len(periods) == 1
    assert periods[0]["period"] == "2025-03-01"
    assert float(periods[0]["income"]) == 700.0


async def test_summary_requires_target_currency_when_multi_currency(
    auth_client, test_user, ref_data, db_session
):
    """Balances in different currencies must never be summed into one number."""
    await _new_currency_account(db_session, test_user, "EUR", "Broker")

    resp = await auth_client.get(
        "/api/analytics/summary",
        params={"date_from": "2025-01-01", "date_to": "2025-01-31"},
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "analytics/currency_required"


async def test_summary_falls_back_to_base_currency(
    auth_client, test_user, ref_data, db_session
):
    """The base currency preference is what resolves an ambiguous multi-currency request."""
    await _new_currency_account(db_session, test_user, "EUR", "Broker")
    test_user.base_currency_code = "USD"
    await db_session.flush()

    resp = await auth_client.get(
        "/api/analytics/summary",
        params={"date_from": "2025-01-01", "date_to": "2025-01-31"},
    )
    assert resp.status_code == 200
    assert resp.json()["rate_coverage"]["base_currency"] == "USD"


async def test_explain_matches_the_summary_row_it_describes(
    auth_client, test_user, ref_data, db_session
):
    """The breakdown must never disagree with the number it is explaining."""
    account = ref_data["account"]
    db_session.add_all(
        [
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=account.id,
                date=date(2025, 1, 31),
                amount=Decimal("1000.00"),
            ),
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=account.id,
                date=date(2025, 2, 28),
                amount=Decimal("1500.00"),
            ),
            Transaction(
                user_id=test_user.id,
                type=TransactionType.income,
                date=date(2025, 2, 10),
                amount=Decimal("2000.00"),
                currency_id=ref_data["currency"].id,
                storage_account_id=account.id,
                income_source_id=ref_data["income_source"].id,
            ),
        ]
    )
    await db_session.flush()

    params = {"date_from": "2025-01-01", "date_to": "2025-02-28", "group_by": "month"}
    summary = await auth_client.get("/api/analytics/summary", params=params)
    feb_row = summary.json()["periods"][1]

    detail = await auth_client.get(
        "/api/analytics/summary/explain",
        params={"period": "2025-02-01", "group_by": "month"},
    )
    assert detail.status_code == 200
    data = detail.json()

    for field in ("income", "profit", "derived_expense"):
        assert float(data[field]) == float(feb_row[field]), field
    assert data["is_measured"] == feb_row["is_measured"]
    assert data["period_end"] == "2025-02-28"


async def test_explain_reports_the_snapshot_dates_behind_a_delta(
    auth_client, test_user, ref_data, db_session
):
    """Snapshots dated well before the period end must be visible as such."""
    account = ref_data["account"]
    db_session.add_all(
        [
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=account.id,
                date=date(2025, 1, 5),
                amount=Decimal("900.00"),
            ),
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=account.id,
                date=date(2025, 2, 3),
                amount=Decimal("400.00"),
            ),
        ]
    )
    await db_session.flush()

    resp = await auth_client.get(
        "/api/analytics/summary/explain",
        params={"period": "2025-02-01", "group_by": "month"},
    )
    assert resp.status_code == 200
    entry = resp.json()["accounts"][0]

    # February's closing balance is really a measurement taken on the 3rd.
    assert entry["opening"]["date"] == "2025-01-05"
    assert entry["closing"]["date"] == "2025-02-03"
    assert float(entry["delta"]) == -500.0
    assert entry["is_opening_capital"] is False
    assert entry["remeasured_in_period"] is True


async def test_explain_flags_an_account_opened_this_period(
    auth_client, test_user, ref_data, db_session
):
    account = ref_data["account"]
    db_session.add(
        BalanceSnapshot(
            user_id=test_user.id,
            storage_account_id=account.id,
            date=date(2025, 1, 31),
            amount=Decimal("700.00"),
        )
    )
    await db_session.flush()

    resp = await auth_client.get(
        "/api/analytics/summary/explain",
        params={"period": "2025-01-01", "group_by": "month"},
    )
    assert resp.status_code == 200
    data = resp.json()
    entry = data["accounts"][0]

    assert entry["opening"] is None
    assert entry["is_opening_capital"] is True
    assert float(data["opening_capital"]["USD"]) == 700.0
    assert float(data["profit"]) == 0.0


async def test_snapshot_timeline_movement_matches_the_summary(
    auth_client, test_user, ref_data, db_session
):
    """The timeline and the dashboard must report the same movement.

    Both now roll up ``split_balance_movement``, so a month whose snapshots fall
    on the period boundaries has to produce one number, not two. This is the
    regression that made the two pages disagree.
    """
    account = ref_data["account"]
    db_session.add_all(
        [
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=account.id,
                date=date(2025, 1, 31),
                amount=Decimal("1000.00"),
            ),
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=account.id,
                date=date(2025, 2, 28),
                amount=Decimal("1750.00"),
            ),
        ]
    )
    await db_session.flush()

    params = {"date_from": "2025-01-01", "date_to": "2025-02-28"}
    summary = await auth_client.get(
        "/api/analytics/summary", params={**params, "group_by": "month"}
    )
    feb_row = summary.json()["periods"][1]

    resp = await auth_client.get("/api/analytics/snapshot-timeline", params=params)
    assert resp.status_code == 200
    entries = resp.json()

    # Newest first, so February leads.
    assert [e["date"] for e in entries] == ["2025-02-28", "2025-01-31"]
    feb_usd = next(c for c in entries[0]["currencies"] if c["code"] == "USD")

    assert float(feb_usd["delta"]) == float(feb_row["balance_change"]["USD"]) == 750.0
    assert float(feb_usd["total"]) == float(feb_row["balances"]["USD"]) == 1750.0


async def test_snapshot_timeline_reports_opening_capital_separately(
    auth_client, test_user, ref_data, db_session
):
    """A newly tracked account must not read as a sudden gain on the timeline."""
    account = ref_data["account"]
    db_session.add_all(
        [
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=account.id,
                date=date(2025, 1, 31),
                amount=Decimal("1000.00"),
            ),
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=account.id,
                date=date(2025, 2, 28),
                amount=Decimal("1200.00"),
            ),
        ]
    )
    second = await _account_at_new_location(
        db_session, test_user, ref_data["currency"].id, "Broker"
    )
    db_session.add(
        BalanceSnapshot(
            user_id=test_user.id,
            storage_account_id=second.id,
            date=date(2025, 2, 28),
            amount=Decimal("500000.00"),
        )
    )
    await db_session.flush()

    resp = await auth_client.get(
        "/api/analytics/snapshot-timeline",
        params={"date_from": "2025-01-01", "date_to": "2025-02-28"},
    )
    assert resp.status_code == 200
    feb = resp.json()[0]
    usd = next(c for c in feb["currencies"] if c["code"] == "USD")

    assert float(usd["delta"]) == 200.0
    assert float(usd["opening_capital"]) == 500000.0
    assert float(usd["total"]) == 501200.0

    broker = next(r for r in feb["rows"] if r["label"] == "Broker USD")
    assert broker["is_opening_capital"] is True
    assert float(broker["delta"]) == 0.0


async def test_snapshot_timeline_compares_against_the_entry_before_the_window(
    auth_client, test_user, ref_data, db_session
):
    """The first visible entry is measured against the snapshot that precedes it.

    Narrowing the date filter must not turn a known movement into a fresh start,
    which is what happens when the comparison is done over the filtered list.
    """
    account = ref_data["account"]
    db_session.add_all(
        [
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=account.id,
                date=date(2025, 1, 31),
                amount=Decimal("1000.00"),
            ),
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=account.id,
                date=date(2025, 2, 28),
                amount=Decimal("1200.00"),
            ),
        ]
    )
    await db_session.flush()

    resp = await auth_client.get(
        "/api/analytics/snapshot-timeline",
        params={"date_from": "2025-02-01", "date_to": "2025-02-28"},
    )
    assert resp.status_code == 200
    entries = resp.json()

    assert [e["date"] for e in entries] == ["2025-02-28"]
    usd = next(c for c in entries[0]["currencies"] if c["code"] == "USD")
    assert float(usd["delta"]) == 200.0
    assert usd["opening_capital"] is None


async def test_snapshot_timeline_marks_carried_forward_rows_uneditable(
    auth_client, test_user, ref_data, db_session
):
    """A row showing last month's number has no snapshot to edit on this date."""
    account = ref_data["account"]
    second = await _account_at_new_location(
        db_session, test_user, ref_data["currency"].id, "Broker"
    )
    db_session.add_all(
        [
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=account.id,
                date=date(2025, 1, 31),
                amount=Decimal("1000.00"),
            ),
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=second.id,
                date=date(2025, 1, 31),
                amount=Decimal("50.00"),
            ),
            BalanceSnapshot(
                user_id=test_user.id,
                storage_account_id=account.id,
                date=date(2025, 2, 28),
                amount=Decimal("1200.00"),
            ),
        ]
    )
    await db_session.flush()

    resp = await auth_client.get(
        "/api/analytics/snapshot-timeline",
        params={"date_from": "2025-01-01", "date_to": "2025-02-28"},
    )
    feb = resp.json()[0]

    assert feb["captured_count"] == 1
    assert len(feb["rows"]) == 2

    carried = next(r for r in feb["rows"] if r["label"] == "Broker USD")
    assert carried["snapshot_id"] is None
    assert carried["since"] == "2025-01-31"

    fresh = next(r for r in feb["rows"] if r["label"] != "Broker USD")
    assert fresh["snapshot_id"] is not None
    assert fresh["since"] == "2025-02-28"


async def test_income_by_source_total_matches_the_summary_income(
    auth_client, test_user, ref_data, db_session
):
    """The donut and the summary row read the same income matrix."""
    account = ref_data["account"]
    db_session.add_all(
        [
            Transaction(
                user_id=test_user.id,
                type=TransactionType.income,
                date=date(2025, 3, 4),
                amount=Decimal("1200.00"),
                currency_id=ref_data["currency"].id,
                storage_account_id=account.id,
                income_source_id=ref_data["income_source"].id,
            ),
            Transaction(
                user_id=test_user.id,
                type=TransactionType.income,
                date=date(2025, 3, 20),
                amount=Decimal("300.00"),
                currency_id=ref_data["currency"].id,
                storage_account_id=account.id,
            ),
        ]
    )
    await db_session.flush()

    params = {"date_from": "2025-03-01", "date_to": "2025-03-31", "group_by": "month"}
    summary = await auth_client.get("/api/analytics/summary", params=params)
    by_source = await auth_client.get("/api/analytics/income-by-source", params=params)

    march_row = summary.json()["periods"][0]
    by_source_body = by_source.json()
    march_sources = by_source_body["periods"][0]

    assert float(march_sources["total"]) == float(march_row["income"]) == 1500.0
    # An income transaction with no source still has to appear somewhere.
    assert float(march_sources["sources"]["Other"]) == 300.0
    # The range total is the same number the summary reports as total income.
    assert (
        float(by_source_body["total"])
        == float(summary.json()["stats"]["total_income"])
        == 1500.0
    )
