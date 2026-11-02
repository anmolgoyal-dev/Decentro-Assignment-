import pytest


def test_health_and_root(client):
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "docs" in res_root.json()


def test_get_group_by_id(client):
    res = client.post("/groups", json={"name": "Kashmir Trek", "description": "Mountain trip"})
    group_id = res.json()["id"]

    get_res = client.get(f"/groups/{group_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Kashmir Trek"

    not_found = client.get("/groups/9999")
    assert not_found.status_code == 404


def test_get_expense_by_id(client):
    u1 = client.post("/users", json={"name": "Alice"}).json()
    u2 = client.post("/users", json={"name": "Bob"}).json()
    g1 = client.post("/groups", json={"name": "Roommates"}).json()
    client.post(f"/groups/{g1['id']}/members", json={"user_id": u1["id"]})
    client.post(f"/groups/{g1['id']}/members", json={"user_id": u2["id"]})

    exp = client.post("/expenses", json={
        "group_id": g1["id"],
        "paid_by": u1["id"],
        "amount": 500.0,
        "description": "Groceries"
    }).json()

    get_exp = client.get(f"/expenses/{exp['id']}")
    assert get_exp.status_code == 200
    assert get_exp.json()["description"] == "Groceries"
    assert get_exp.json()["paid_by"] == "Alice"

    not_found = client.get("/expenses/9999")
    assert not_found.status_code == 404


def test_list_settlements_and_filtering(client):
    u1 = client.post("/users", json={"name": "User 1"}).json()
    u2 = client.post("/users", json={"name": "User 2"}).json()
    g1 = client.post("/groups", json={"name": "Group 1"}).json()
    client.post(f"/groups/{g1['id']}/members", json={"user_id": u1["id"]})
    client.post(f"/groups/{g1['id']}/members", json={"user_id": u2["id"]})

    s1 = client.post("/settlements", json={
        "payer_id": u1["id"],
        "payee_id": u2["id"],
        "amount": 250.0,
        "group_id": g1["id"],
        "notes": "Cash settlement"
    }).json()

    # List all settlements
    res = client.get("/settlements")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["notes"] == "Cash settlement"

    # List with group filter
    res_filter = client.get(f"/settlements?group_id={g1['id']}")
    assert res_filter.status_code == 200
    assert len(res_filter.json()) == 1


def test_expense_on_empty_group_fails(client):
    u1 = client.post("/users", json={"name": "Lonely User"}).json()
    g1 = client.post("/groups", json={"name": "Empty Group"}).json()

    res = client.post("/expenses", json={
        "group_id": g1["id"],
        "paid_by": u1["id"],
        "amount": 100.0,
        "description": "Fail"
    })
    assert res.status_code == 400
    assert "no members" in res.json()["detail"]


def test_settlement_validations(client):
    u1 = client.post("/users", json={"name": "Mohit"}).json()
    u2 = client.post("/users", json={"name": "Rahul"}).json()
    outsider = client.post("/users", json={"name": "Outsider"}).json()
    g1 = client.post("/groups", json={"name": "Goa Trip"}).json()
    client.post(f"/groups/{g1['id']}/members", json={"user_id": u1["id"]})
    client.post(f"/groups/{g1['id']}/members", json={"user_id": u2["id"]})

    # Payer does not exist
    res1 = client.post("/settlements", json={
        "payer_id": 9999,
        "payee_id": u1["id"],
        "amount": 100.0
    })
    assert res1.status_code == 404

    # Payee does not exist
    res2 = client.post("/settlements", json={
        "payer_id": u1["id"],
        "payee_id": 9999,
        "amount": 100.0
    })
    assert res2.status_code == 404

    # Group does not exist
    res3 = client.post("/settlements", json={
        "payer_id": u1["id"],
        "payee_id": u2["id"],
        "amount": 100.0,
        "group_id": 9999
    })
    assert res3.status_code == 404

    # Payer not in group
    res4 = client.post("/settlements", json={
        "payer_id": outsider["id"],
        "payee_id": u1["id"],
        "amount": 100.0,
        "group_id": g1["id"]
    })
    assert res4.status_code == 400
