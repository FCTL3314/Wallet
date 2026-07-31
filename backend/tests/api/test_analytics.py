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
    assert float(jan["profit"]) == 2500.0
    assert jan["is_bootstrap"] is True
    assert float(jan["derived_expense"]) == 0.0

    feb = periods[1]
    assert float(feb["income"]) == 3200.0
    assert float(feb["profit"]) == 2600.0
    assert feb["is_bootstrap"] is False
    assert float(feb["derived_expense"]) == 600.0


async def test_summary_income_only_no_snapshots(
    auth_client, test_user, ref_data, db_session
):
    """Income with no snapshots: profit=0, derived_expense=income."""
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
    assert float(row["derived_expense"]) == 4000.0


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
    assert len(data) == 2
    # Each period should have the "Salary" source
    for period in data:
        assert "Salary" in period["sources"]


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
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["latest_snapshot_date"] == "2025-06-30"
    assert float(rows[0]["latest_snapshot_amount"]) == 5000.0


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
