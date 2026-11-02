from decimal import Decimal
import pytest


def setup_trip_group(client):
    """Helper to create Mohit, Rahul, Ankit in Goa Trip."""
    u1 = client.post("/users", json={"name": "Mohit"}).json()
    u2 = client.post("/users", json={"name": "Rahul"}).json()
    u3 = client.post("/users", json={"name": "Ankit"}).json()
    g1 = client.post("/groups", json={"name": "Goa Trip"}).json()

    for u in [u1, u2, u3]:
        client.post(f"/groups/{g1['id']}/members", json={"user_id": u["id"]})

    return u1, u2, u3, g1


def test_add_expense_equal_split_pdf_scenario(client):
    u1, u2, u3, g1 = setup_trip_group(client)

    payload = {
        "group_id": g1["id"],
        "paid_by": u1["id"],
        "amount": 1200.0,
        "description": "Dinner"
    }
    response = client.post("/expenses", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["description"] == "Dinner"
    assert float(data["amount"]) == 1200.0
    assert data["paid_by"] == "Mohit"
    assert len(data["splits"]) == 3

    # Each person owes 400
    for split in data["splits"]:
        assert float(split["amount_owed"]) == 400.0


def test_list_group_expenses(client):
    u1, u2, u3, g1 = setup_trip_group(client)

    client.post("/expenses", json={
        "group_id": g1["id"],
        "paid_by": u1["id"],
        "amount": 1200.0,
        "description": "Dinner"
    })
    client.post("/expenses", json={
        "group_id": g1["id"],
        "paid_by": u2["id"],
        "amount": 600.0,
        "description": "Scuba Diving"
    })

    res = client.get(f"/groups/{g1['id']}/expenses")
    assert res.status_code == 200
    expenses = res.json()
    assert len(expenses) == 2
    assert expenses[0]["description"] == "Dinner"
    assert expenses[0]["paid_by"] == "Mohit"
    assert float(expenses[0]["amount"]) == 1200.0
    assert expenses[1]["description"] == "Scuba Diving"
    assert expenses[1]["paid_by"] == "Rahul"
    assert float(expenses[1]["amount"]) == 600.0


def test_equal_split_penny_precision(client):
    """
    Ensure splitting amounts like ₹100 among 3 users (33.333...) does not leak cents.
    Expected: 33.34 + 33.33 + 33.33 = 100.00
    """
    u1, u2, u3, g1 = setup_trip_group(client)

    res = client.post("/expenses", json={
        "group_id": g1["id"],
        "paid_by": u1["id"],
        "amount": 100.0,
        "description": "Snacks"
    })
    assert res.status_code == 201
    data = res.json()

    splits = data["splits"]
    total_split = sum(Decimal(str(s["amount_owed"])) for s in splits)
    assert total_split == Decimal("100.00")

    shares = sorted([float(s["amount_owed"]) for s in splits], reverse=True)
    assert shares == [33.34, 33.33, 33.33]


def test_custom_exact_split_success(client):
    u1, u2, u3, g1 = setup_trip_group(client)

    payload = {
        "group_id": g1["id"],
        "paid_by": u1["id"],
        "amount": 1000.0,
        "description": "Custom Drinks",
        "split_type": "EXACT",
        "splits": [
            {"user_id": u1["id"], "amount": 500.0},
            {"user_id": u2["id"], "amount": 300.0},
            {"user_id": u3["id"], "amount": 200.0}
        ]
    }
    res = client.post("/expenses", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert float(data["amount"]) == 1000.0
    assert len(data["splits"]) == 3


def test_custom_split_mismatch_amount_fails(client):
    u1, u2, u3, g1 = setup_trip_group(client)

    payload = {
        "group_id": g1["id"],
        "paid_by": u1["id"],
        "amount": 1000.0,
        "description": "Bad Math",
        "split_type": "EXACT",
        "splits": [
            {"user_id": u1["id"], "amount": 500.0},
            {"user_id": u2["id"], "amount": 300.0}  # total only 800
        ]
    }
    res = client.post("/expenses", json=payload)
    assert res.status_code == 400
    assert "Sum of custom splits" in res.json()["detail"]


def test_expense_validation_non_member_payer(client):
    u1, u2, u3, g1 = setup_trip_group(client)
    outsider = client.post("/users", json={"name": "Outsider"}).json()

    res = client.post("/expenses", json={
        "group_id": g1["id"],
        "paid_by": outsider["id"],
        "amount": 500.0,
        "description": "Failed expense"
    })
    assert res.status_code == 400
    assert "is not a member of group" in res.json()["detail"]


def test_expense_validation_negative_or_zero_amount(client):
    u1, u2, u3, g1 = setup_trip_group(client)

    res_zero = client.post("/expenses", json={
        "group_id": g1["id"],
        "paid_by": u1["id"],
        "amount": 0.0,
        "description": "Zero"
    })
    assert res_zero.status_code == 422

    res_neg = client.post("/expenses", json={
        "group_id": g1["id"],
        "paid_by": u1["id"],
        "amount": -50.0,
        "description": "Negative"
    })
    assert res_neg.status_code == 422
