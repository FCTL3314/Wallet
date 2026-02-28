import pytest


# --- Storage Locations ---


async def test_create_location(auth_client):
    resp = await auth_client.post(
        "/api/storage-locations/", json={"name": "Bank"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Bank"
    assert "id" in data


async def test_update_location(auth_client):
    create = await auth_client.post(
        "/api/storage-locations/", json={"name": "Old"}
    )
    lid = create.json()["id"]
    resp = await auth_client.put(
        f"/api/storage-locations/{lid}", json={"name": "New"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"


async def test_delete_location(auth_client):
    create = await auth_client.post(
        "/api/storage-locations/", json={"name": "Temp"}
    )
    lid = create.json()["id"]
    resp = await auth_client.delete(f"/api/storage-locations/{lid}")
    assert resp.status_code == 204


async def test_delete_location_nonexistent(auth_client):
    resp = await auth_client.delete("/api/storage-locations/99999")
    assert resp.status_code == 404


# --- Storage Accounts ---


async def _create_loc_and_cur(auth_client):
    """Helper to create a location and currency, returns (loc_id, cur_id)."""
    loc = await auth_client.post(
        "/api/storage-locations/", json={"name": "Bank"}
    )
    cur = await auth_client.post(
        "/api/currencies/", json={"code": "USD", "symbol": "$"}
    )
    return loc.json()["id"], cur.json()["id"]


async def test_create_account(auth_client):
    loc_id, cur_id = await _create_loc_and_cur(auth_client)
    resp = await auth_client.post(
        "/api/storage-accounts/",
        json={"storage_location_id": loc_id, "currency_id": cur_id},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["storage_location_id"] == loc_id
    assert data["currency_id"] == cur_id


async def test_list_accounts_with_nested(auth_client):
    loc_id, cur_id = await _create_loc_and_cur(auth_client)
    await auth_client.post(
        "/api/storage-accounts/",
        json={"storage_location_id": loc_id, "currency_id": cur_id},
    )
    resp = await auth_client.get("/api/storage-accounts/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["storage_location"]["name"] == "Bank"
    assert data[0]["currency"]["code"] == "USD"


async def test_update_account_location(auth_client):
    loc_id, cur_id = await _create_loc_and_cur(auth_client)
    acc = await auth_client.post(
        "/api/storage-accounts/",
        json={"storage_location_id": loc_id, "currency_id": cur_id},
    )
    acc_id = acc.json()["id"]

    new_loc = await auth_client.post(
        "/api/storage-locations/", json={"name": "Wallet"}
    )
    new_loc_id = new_loc.json()["id"]

    resp = await auth_client.put(
        f"/api/storage-accounts/{acc_id}",
        json={"storage_location_id": new_loc_id},
    )
    assert resp.status_code == 200
    assert resp.json()["storage_location_id"] == new_loc_id


async def test_delete_account(auth_client):
    loc_id, cur_id = await _create_loc_and_cur(auth_client)
    acc = await auth_client.post(
        "/api/storage-accounts/",
        json={"storage_location_id": loc_id, "currency_id": cur_id},
    )
    resp = await auth_client.delete(f"/api/storage-accounts/{acc.json()['id']}")
    assert resp.status_code == 204


async def test_delete_account_nonexistent(auth_client):
    resp = await auth_client.delete("/api/storage-accounts/99999")
    assert resp.status_code == 404
