async def test_list_empty(auth_client):
    resp = await auth_client.get("/api/currencies/")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create(auth_client):
    resp = await auth_client.post(
        "/api/currencies/", json={"code": "EUR", "symbol": "€"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == "EUR"
    assert data["symbol"] == "€"
    assert "id" in data


async def test_list_after_create(auth_client):
    await auth_client.post("/api/currencies/", json={"code": "GBP", "symbol": "£"})
    resp = await auth_client.get("/api/currencies/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_update(auth_client):
    create = await auth_client.post(
        "/api/currencies/", json={"code": "JPY", "symbol": "¥"}
    )
    cid = create.json()["id"]
    resp = await auth_client.put(f"/api/currencies/{cid}", json={"symbol": "円"})
    assert resp.status_code == 200
    assert resp.json()["symbol"] == "円"
    assert resp.json()["code"] == "JPY"


async def test_delete(auth_client):
    create = await auth_client.post(
        "/api/currencies/", json={"code": "CHF", "symbol": "Fr"}
    )
    cid = create.json()["id"]
    resp = await auth_client.delete(f"/api/currencies/{cid}")
    assert resp.status_code == 204

    listing = await auth_client.get("/api/currencies/")
    assert len(listing.json()) == 0


async def test_delete_nonexistent(auth_client):
    resp = await auth_client.delete("/api/currencies/99999")
    assert resp.status_code == 404


async def test_multi_tenancy(auth_client, other_auth_client):
    # User A creates a currency
    create = await auth_client.post(
        "/api/currencies/", json={"code": "USD", "symbol": "$"}
    )
    assert create.status_code == 201

    # User B should not see it
    resp = await other_auth_client.get("/api/currencies/")
    assert resp.status_code == 200
    assert len(resp.json()) == 0
