async def test_list_empty(auth_client):
    resp = await auth_client.get("/api/income-sources/")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create(auth_client):
    resp = await auth_client.post(
        "/api/income-sources/", json={"name": "Freelance"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Freelance"
    assert "id" in data


async def test_list_after_create(auth_client):
    await auth_client.post("/api/income-sources/", json={"name": "Salary"})
    resp = await auth_client.get("/api/income-sources/")
    assert len(resp.json()) == 1


async def test_update(auth_client):
    create = await auth_client.post(
        "/api/income-sources/", json={"name": "Old Name"}
    )
    sid = create.json()["id"]
    resp = await auth_client.put(
        f"/api/income-sources/{sid}", json={"name": "New Name"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


async def test_delete(auth_client):
    create = await auth_client.post(
        "/api/income-sources/", json={"name": "Temp"}
    )
    sid = create.json()["id"]
    resp = await auth_client.delete(f"/api/income-sources/{sid}")
    assert resp.status_code == 204


async def test_delete_nonexistent(auth_client):
    resp = await auth_client.delete("/api/income-sources/99999")
    assert resp.status_code == 404
