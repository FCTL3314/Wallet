async def test_create(auth_client, ref_data):
    resp = await auth_client.post(
        "/api/balance-snapshots/",
        json={
            "storage_account_id": ref_data["account"].id,
            "date": "2025-01-31",
            "amount": "5000.00",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert float(data["amount"]) == 5000.0
    assert data["storage_account_id"] == ref_data["account"].id


async def test_update(auth_client, ref_data):
    create = await auth_client.post(
        "/api/balance-snapshots/",
        json={
            "storage_account_id": ref_data["account"].id,
            "date": "2025-02-28",
            "amount": "1000.00",
        },
    )
    sid = create.json()["id"]
    resp = await auth_client.put(
        f"/api/balance-snapshots/{sid}", json={"amount": "2000.00"}
    )
    assert resp.status_code == 200
    assert float(resp.json()["amount"]) == 2000.0


async def test_delete(auth_client, ref_data):
    create = await auth_client.post(
        "/api/balance-snapshots/",
        json={
            "storage_account_id": ref_data["account"].id,
            "date": "2025-03-31",
            "amount": "100.00",
        },
    )
    sid = create.json()["id"]
    resp = await auth_client.delete(f"/api/balance-snapshots/{sid}")
    assert resp.status_code == 204


async def test_amount_zero_rejected(auth_client, ref_data):
    resp = await auth_client.post(
        "/api/balance-snapshots/",
        json={
            "storage_account_id": ref_data["account"].id,
            "date": "2025-04-30",
            "amount": "0",
        },
    )
    assert resp.status_code == 422


async def test_amount_negative_rejected(auth_client, ref_data):
    resp = await auth_client.post(
        "/api/balance-snapshots/",
        json={
            "storage_account_id": ref_data["account"].id,
            "date": "2025-04-30",
            "amount": "-100",
        },
    )
    assert resp.status_code == 422


async def test_filter_by_storage_account(auth_client, ref_data, db_session, test_user):
    from app.models import Currency, StorageAccount, StorageLocation

    # Create a second account
    cur2 = Currency(code="EUR", symbol="€", user_id=test_user.id)
    db_session.add(cur2)
    await db_session.flush()
    loc2 = StorageLocation(name="Broker", user_id=test_user.id)
    db_session.add(loc2)
    await db_session.flush()
    acc2 = StorageAccount(
        storage_location_id=loc2.id, currency_id=cur2.id, user_id=test_user.id
    )
    db_session.add(acc2)
    await db_session.flush()

    # Create snapshots on each account
    await auth_client.post(
        "/api/balance-snapshots/",
        json={
            "storage_account_id": ref_data["account"].id,
            "date": "2025-05-31",
            "amount": "100.00",
        },
    )
    await auth_client.post(
        "/api/balance-snapshots/",
        json={
            "storage_account_id": acc2.id,
            "date": "2025-05-31",
            "amount": "200.00",
        },
    )

    resp = await auth_client.get(
        "/api/balance-snapshots/",
        params={"storage_account_id": ref_data["account"].id},
    )
    assert resp.status_code == 200
    assert all(
        s["storage_account_id"] == ref_data["account"].id for s in resp.json()
    )


async def test_filter_by_date_range(auth_client, ref_data):
    for d in ("2025-01-31", "2025-06-30", "2025-12-31"):
        await auth_client.post(
            "/api/balance-snapshots/",
            json={
                "storage_account_id": ref_data["account"].id,
                "date": d,
                "amount": "500.00",
            },
        )

    resp = await auth_client.get(
        "/api/balance-snapshots/",
        params={"date_from": "2025-04-01", "date_to": "2025-09-30"},
    )
    assert resp.status_code == 200
    dates = [s["date"] for s in resp.json()]
    assert all("2025-04-01" <= d <= "2025-09-30" for d in dates)


async def test_delete_nonexistent(auth_client):
    resp = await auth_client.delete("/api/balance-snapshots/99999")
    assert resp.status_code == 404
