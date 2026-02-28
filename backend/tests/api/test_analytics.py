from datetime import date
from decimal import Decimal

from app.models import BalanceSnapshot, Transaction
from app.models.transaction import TransactionType


async def _seed_transactions(db_session, user, ref_data):
    """Create a set of transactions for analytics tests."""
    account = ref_data["account"]
    currency = ref_data["currency"]
    income_source = ref_data["income_source"]
    expense_category = ref_data["expense_category"]

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
            type=TransactionType.expense,
            date=date(2025, 1, 20),
            amount=Decimal("500.00"),
            currency_id=currency.id,
            storage_account_id=account.id,
            expense_category_id=expense_category.id,
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
        Transaction(
            user_id=user.id,
            type=TransactionType.expense,
            date=date(2025, 2, 20),
            amount=Decimal("600.00"),
            currency_id=currency.id,
            storage_account_id=account.id,
            expense_category_id=expense_category.id,
        ),
    ]
    for t in txns:
        db_session.add(t)
    await db_session.flush()
    return txns


async def test_summary_empty_period(auth_client, test_user, ref_data):
    resp = await auth_client.get(
        "/api/analytics/summary",
        params={"date_from": "2099-01-01", "date_to": "2099-12-31"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_summary_with_transactions(
    auth_client, test_user, ref_data, db_session
):
    await _seed_transactions(db_session, test_user, ref_data)

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
    assert len(data) == 2

    jan = data[0]
    assert float(jan["income"]) == 3000.0
    assert float(jan["expenses"]) == 500.0
    assert float(jan["profit"]) == 2500.0


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
    assert len(data) == 1
    assert "balances" in data[0]
    assert float(data[0]["balances"]["USD"]) == 10000.0


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


async def test_expense_template(auth_client, test_user, ref_data, db_session):
    from app.models import ExpenseCategory

    tax_cat = ExpenseCategory(
        name="Tax",
        budgeted_amount=Decimal("200.00"),
        is_tax=True,
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


async def test_expense_vs_budget_with_transactions(
    auth_client, test_user, ref_data, db_session
):
    # Create a transaction for January
    db_session.add(
        Transaction(
            user_id=test_user.id,
            type=TransactionType.expense,
            date=date(2025, 1, 15),
            amount=Decimal("300.00"),
            currency_id=ref_data["currency"].id,
            storage_account_id=ref_data["account"].id,
            expense_category_id=ref_data["expense_category"].id,
        )
    )
    await db_session.flush()

    resp = await auth_client.get(
        "/api/analytics/expense-vs-budget",
        params={"year": 2025, "month": 1},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    item = data[0]
    assert item["name"] == "Food"
    assert float(item["budgeted"]) == 500.0
    assert float(item["actual"]) == 300.0
    assert float(item["remaining"]) == 200.0


async def test_expense_vs_budget_no_transactions(
    auth_client, test_user, ref_data
):
    resp = await auth_client.get(
        "/api/analytics/expense-vs-budget",
        params={"year": 2099, "month": 1},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert float(data[0]["actual"]) == 0
    assert float(data[0]["remaining"]) == 500.0
