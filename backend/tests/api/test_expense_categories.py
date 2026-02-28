async def test_list_empty(auth_client):
    resp = await auth_client.get("/api/expense-categories/")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_defaults(auth_client):
    resp = await auth_client.post(
        "/api/expense-categories/", json={"name": "Transport"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Transport"
    assert float(data["budgeted_amount"]) == 0.0
    assert data["is_tax"] is False
    assert data["is_rent"] is False


async def test_create_with_all_fields(auth_client):
    resp = await auth_client.post(
        "/api/expense-categories/",
        json={
            "name": "Rent",
            "budgeted_amount": "1200.00",
            "is_tax": False,
            "is_rent": True,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert float(data["budgeted_amount"]) == 1200.0
    assert data["is_rent"] is True


async def test_update_budgeted_amount(auth_client):
    create = await auth_client.post(
        "/api/expense-categories/", json={"name": "Food"}
    )
    cid = create.json()["id"]
    resp = await auth_client.put(
        f"/api/expense-categories/{cid}", json={"budgeted_amount": "750.50"}
    )
    assert resp.status_code == 200
    assert float(resp.json()["budgeted_amount"]) == 750.5


async def test_update_flags(auth_client):
    create = await auth_client.post(
        "/api/expense-categories/", json={"name": "Tax"}
    )
    cid = create.json()["id"]
    resp = await auth_client.put(
        f"/api/expense-categories/{cid}", json={"is_tax": True}
    )
    assert resp.status_code == 200
    assert resp.json()["is_tax"] is True


async def test_delete(auth_client):
    create = await auth_client.post(
        "/api/expense-categories/", json={"name": "Temp"}
    )
    cid = create.json()["id"]
    resp = await auth_client.delete(f"/api/expense-categories/{cid}")
    assert resp.status_code == 204


async def test_delete_nonexistent(auth_client):
    resp = await auth_client.delete("/api/expense-categories/99999")
    assert resp.status_code == 404
