from datetime import date


async def test_create_income(auth_client, ref_data):
    resp = await auth_client.post(
        "/api/transactions/",
        json={
            "type": "income",
            "date": "2025-01-15",
            "amount": "3000.00",
            "currency_id": ref_data["currency"].id,
            "storage_account_id": ref_data["account"].id,
            "income_source_id": ref_data["income_source"].id,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "income"
    assert float(data["amount"]) == 3000.0


async def test_create_expense(auth_client, ref_data):
    resp = await auth_client.post(
        "/api/transactions/",
        json={
            "type": "expense",
            "date": "2025-01-16",
            "amount": "50.00",
            "currency_id": ref_data["currency"].id,
            "storage_account_id": ref_data["account"].id,
            "expense_category_id": ref_data["expense_category"].id,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["type"] == "expense"


async def test_update_transaction(auth_client, ref_data):
    create = await auth_client.post(
        "/api/transactions/",
        json={
            "type": "income",
            "date": "2025-02-01",
            "amount": "100.00",
            "currency_id": ref_data["currency"].id,
            "storage_account_id": ref_data["account"].id,
        },
    )
    tid = create.json()["id"]
    resp = await auth_client.put(
        f"/api/transactions/{tid}", json={"amount": "200.00"}
    )
    assert resp.status_code == 200
    assert float(resp.json()["amount"]) == 200.0


async def test_delete_transaction(auth_client, ref_data):
    create = await auth_client.post(
        "/api/transactions/",
        json={
            "type": "income",
            "date": "2025-02-02",
            "amount": "100.00",
            "currency_id": ref_data["currency"].id,
            "storage_account_id": ref_data["account"].id,
        },
    )
    tid = create.json()["id"]
    resp = await auth_client.delete(f"/api/transactions/{tid}")
    assert resp.status_code == 204


async def test_amount_zero_rejected(auth_client, ref_data):
    resp = await auth_client.post(
        "/api/transactions/",
        json={
            "type": "income",
            "date": "2025-03-01",
            "amount": "0",
            "currency_id": ref_data["currency"].id,
            "storage_account_id": ref_data["account"].id,
        },
    )
    assert resp.status_code == 422


async def test_amount_negative_rejected(auth_client, ref_data):
    resp = await auth_client.post(
        "/api/transactions/",
        json={
            "type": "income",
            "date": "2025-03-01",
            "amount": "-10",
            "currency_id": ref_data["currency"].id,
            "storage_account_id": ref_data["account"].id,
        },
    )
    assert resp.status_code == 422


async def test_fk_ownership_income_source(
    auth_client, other_user, db_session, ref_data
):
    """income_source_id belonging to another user should be rejected."""
    from app.models import IncomeSource

    other_source = IncomeSource(name="Other Salary", user_id=other_user.id)
    db_session.add(other_source)
    await db_session.flush()

    resp = await auth_client.post(
        "/api/transactions/",
        json={
            "type": "income",
            "date": "2025-04-01",
            "amount": "100.00",
            "currency_id": ref_data["currency"].id,
            "storage_account_id": ref_data["account"].id,
            "income_source_id": other_source.id,
        },
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "resource/income_source_not_found"


async def test_fk_ownership_expense_category(
    auth_client, other_user, db_session, ref_data
):
    """expense_category_id belonging to another user should be rejected."""
    from app.models import ExpenseCategory

    other_cat = ExpenseCategory(name="Other Food", user_id=other_user.id)
    db_session.add(other_cat)
    await db_session.flush()

    resp = await auth_client.post(
        "/api/transactions/",
        json={
            "type": "expense",
            "date": "2025-04-01",
            "amount": "100.00",
            "currency_id": ref_data["currency"].id,
            "storage_account_id": ref_data["account"].id,
            "expense_category_id": other_cat.id,
        },
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "resource/expense_category_not_found"


async def test_filter_by_type(auth_client, ref_data):
    for tx_type in ("income", "expense"):
        await auth_client.post(
            "/api/transactions/",
            json={
                "type": tx_type,
                "date": "2025-05-01",
                "amount": "100.00",
                "currency_id": ref_data["currency"].id,
                "storage_account_id": ref_data["account"].id,
            },
        )

    resp = await auth_client.get("/api/transactions/", params={"type": "income"})
    assert resp.status_code == 200
    assert all(t["type"] == "income" for t in resp.json())


async def test_filter_by_date_range(auth_client, ref_data):
    for d in ("2025-01-01", "2025-06-01", "2025-12-01"):
        await auth_client.post(
            "/api/transactions/",
            json={
                "type": "income",
                "date": d,
                "amount": "100.00",
                "currency_id": ref_data["currency"].id,
                "storage_account_id": ref_data["account"].id,
            },
        )

    resp = await auth_client.get(
        "/api/transactions/",
        params={"date_from": "2025-03-01", "date_to": "2025-09-01"},
    )
    assert resp.status_code == 200
    dates = [t["date"] for t in resp.json()]
    assert all("2025-03-01" <= d <= "2025-09-01" for d in dates)


async def test_filter_by_income_source(auth_client, ref_data):
    await auth_client.post(
        "/api/transactions/",
        json={
            "type": "income",
            "date": "2025-07-01",
            "amount": "100.00",
            "currency_id": ref_data["currency"].id,
            "storage_account_id": ref_data["account"].id,
            "income_source_id": ref_data["income_source"].id,
        },
    )
    await auth_client.post(
        "/api/transactions/",
        json={
            "type": "income",
            "date": "2025-07-02",
            "amount": "200.00",
            "currency_id": ref_data["currency"].id,
            "storage_account_id": ref_data["account"].id,
        },
    )

    resp = await auth_client.get(
        "/api/transactions/",
        params={"income_source_id": ref_data["income_source"].id},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["income_source_id"] == ref_data["income_source"].id


async def test_pagination(auth_client, ref_data):
    for i in range(5):
        await auth_client.post(
            "/api/transactions/",
            json={
                "type": "income",
                "date": f"2025-08-{i+1:02d}",
                "amount": "10.00",
                "currency_id": ref_data["currency"].id,
                "storage_account_id": ref_data["account"].id,
            },
        )

    page1 = await auth_client.get(
        "/api/transactions/", params={"limit": 2, "offset": 0}
    )
    page2 = await auth_client.get(
        "/api/transactions/", params={"limit": 2, "offset": 2}
    )
    assert len(page1.json()) == 2
    assert len(page2.json()) == 2
    ids1 = {t["id"] for t in page1.json()}
    ids2 = {t["id"] for t in page2.json()}
    assert ids1.isdisjoint(ids2)


async def test_multi_tenancy(auth_client, other_auth_client, ref_data):
    await auth_client.post(
        "/api/transactions/",
        json={
            "type": "income",
            "date": "2025-09-01",
            "amount": "999.00",
            "currency_id": ref_data["currency"].id,
            "storage_account_id": ref_data["account"].id,
        },
    )

    resp = await other_auth_client.get("/api/transactions/")
    assert resp.status_code == 200
    assert len(resp.json()) == 0
