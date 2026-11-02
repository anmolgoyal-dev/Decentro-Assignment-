import pytest


def setup_trip(client):
    u1 = client.post("/users", json={"name": "Mohit"}).json()
    u2 = client.post("/users", json={"name": "Rahul"}).json()
    u3 = client.post("/users", json={"name": "Ankit"}).json()
    g1 = client.post("/groups", json={"name": "Goa Trip"}).json()

    for u in [u1, u2, u3]:
        client.post(f"/groups/{g1['id']}/members", json={"user_id": u["id"]})

    return u1, u2, u3, g1


def test_full_settlement_clears_balance(client):
    """
    Rahul owes Mohit ₹400.
    Rahul settles ₹400 with Mohit.
    Rahul now owes Mohit ₹0.
    """
    u1, u2, u3, g1 = setup_trip(client)

    # 1. Dinner ₹1200 paid by Mohit
    client.post("/expenses", json={
        "group_id": g1["id"],
        "paid_by": u1["id"],
        "amount": 1200.0,
        "description": "Dinner"
    })

    # Before settlement: Rahul owes Mohit 400
    bal_before = client.get(f"/groups/{g1['id']}/balances").json()
    assert bal_before["Rahul"]["owes"]["Mohit"] == 400.0

    # 2. Record settlement: Rahul pays Mohit 400
    settle_res = client.post("/settlements", json={
        "payer_id": u2["id"],
        "payee_id": u1["id"],
        "amount": 400.0,
        "group_id": g1["id"],
        "notes": "UPI transfer"
    })
    assert settle_res.status_code == 201
    settle_data = settle_res.json()
    assert settle_data["payer_name"] == "Rahul"
    assert settle_data["payee_name"] == "Mohit"
    assert float(settle_data["amount"]) == 400.0

    # After settlement: Rahul owes Mohit 0, so Rahul does not owe Mohit any balance
    bal_after = client.get(f"/groups/{g1['id']}/balances").json()
    assert "Rahul" not in bal_after or "Mohit" not in bal_after.get("Rahul", {}).get("owes", {})

    # Ankit still owes Mohit 400
    assert bal_after["Ankit"]["owes"]["Mohit"] == 400.0


def test_partial_settlement(client):
    u1, u2, u3, g1 = setup_trip(client)

    client.post("/expenses", json={
        "group_id": g1["id"],
        "paid_by": u1["id"],
        "amount": 1200.0,
        "description": "Dinner"
    })

    # Rahul pays 150 out of 400
    client.post("/settlements", json={
        "payer_id": u2["id"],
        "payee_id": u1["id"],
        "amount": 150.0,
        "group_id": g1["id"]
    })

    bal = client.get(f"/groups/{g1['id']}/balances").json()
    assert bal["Rahul"]["owes"]["Mohit"] == 250.0


def test_smart_settlement_suggestions_simplification(client):
    """
    Test Debt Simplification (Min-Cash-Flow):
    Scenario:
    - Alice, Bob, Charlie in Group
    - Alice pays 300 for an expense where only Bob owes 300 (Bob owes Alice 300).
    - Bob pays 300 for an expense where only Charlie owes 300 (Charlie owes Bob 300).
    Unsimplified:
      Charlie -> Bob: 300
      Bob -> Alice: 300
      (2 transactions)
    Simplified Min-Cash-Flow:
      Charlie -> Alice: 300
      (1 transaction! Bob does nothing!)
    """
    alice = client.post("/users", json={"name": "Alice"}).json()
    bob = client.post("/users", json={"name": "Bob"}).json()
    charlie = client.post("/users", json={"name": "Charlie"}).json()
    group = client.post("/groups", json={"name": "Test Group"}).json()

    for u in [alice, bob, charlie]:
        client.post(f"/groups/{group['id']}/members", json={"user_id": u["id"]})

    # Expense 1: Alice pays 300, only Bob owes 300
    client.post("/expenses", json={
        "group_id": group["id"],
        "paid_by": alice["id"],
        "amount": 300.0,
        "description": "Alice to Bob",
        "split_type": "EXACT",
        "splits": [
            {"user_id": bob["id"], "amount": 300.0}
        ]
    })

    # Expense 2: Bob pays 300, only Charlie owes 300
    client.post("/expenses", json={
        "group_id": group["id"],
        "paid_by": bob["id"],
        "amount": 300.0,
        "description": "Bob to Charlie",
        "split_type": "EXACT",
        "splits": [
            {"user_id": charlie["id"], "amount": 300.0}
        ]
    })

    # Pairwise debts before simplification: 2 transactions
    bal_res = client.get(f"/groups/{group['id']}/balances").json()
    assert bal_res["Bob"]["owes"]["Alice"] == 300.0
    assert bal_res["Charlie"]["owes"]["Bob"] == 300.0

    # Smart Settlement Suggestions
    sug_res = client.get(f"/groups/{group['id']}/settlements/suggestions")
    assert sug_res.status_code == 200
    data = sug_res.json()

    assert data["total_transactions_before"] == 2
    assert data["simplified_transactions_count"] == 1

    suggestion = data["suggestions"][0]
    assert suggestion["from_user_name"] == "Charlie"
    assert suggestion["to_user_name"] == "Alice"
    assert float(suggestion["amount"]) == 300.0


def test_settlement_validation_self_pay_rejected(client):
    u1, u2, u3, g1 = setup_trip(client)

    res = client.post("/settlements", json={
        "payer_id": u1["id"],
        "payee_id": u1["id"],
        "amount": 100.0
    })
    assert res.status_code == 400
    assert "cannot be the same" in res.json()["detail"]
