import pytest


def setup_trip(client):
    u1 = client.post("/users", json={"name": "Mohit"}).json()
    u2 = client.post("/users", json={"name": "Rahul"}).json()
    u3 = client.post("/users", json={"name": "Ankit"}).json()
    g1 = client.post("/groups", json={"name": "Goa Trip"}).json()

    for u in [u1, u2, u3]:
        client.post(f"/groups/{g1['id']}/members", json={"user_id": u["id"]})

    return u1, u2, u3, g1


def test_balance_calculation_exact_pdf_scenario(client):
    """
    Verifies the exact scenario described in the PDF:
    Users: Mohit, Rahul, Ankit
    Group: Goa Trip
    Expense: Dinner = ₹1200 Paid by Mohit
    Participants: Mohit, Rahul, Ankit (₹400 per person)
    Expected Balance View:
      Rahul -> Mohit: ₹400
      Ankit -> Mohit: ₹400
    JSON format:
    {
      "Rahul": { "owes": { "Mohit": 400.0 } },
      "Ankit": { "owes": { "Mohit": 400.0 } }
    }
    """
    u1, u2, u3, g1 = setup_trip(client)

    client.post("/expenses", json={
        "group_id": g1["id"],
        "paid_by": u1["id"],
        "amount": 1200.0,
        "description": "Dinner"
    })

    # Test global /balances endpoint
    res = client.get("/balances")
    assert res.status_code == 200
    balances = res.json()

    assert "Rahul" in balances
    assert balances["Rahul"]["owes"] == {"Mohit": 400.0}

    assert "Ankit" in balances
    assert balances["Ankit"]["owes"] == {"Mohit": 400.0}

    # Payer (Mohit) should not owe themselves or appear with debts
    assert "Mohit" not in balances or len(balances.get("Mohit", {}).get("owes", {})) == 0

    # Test group-specific /groups/{group_id}/balances endpoint
    res_group = client.get(f"/groups/{g1['id']}/balances")
    assert res_group.status_code == 200
    assert res_group.json() == balances


def test_multi_expense_cross_netting_balances(client):
    """
    Expense 1: Mohit pays ₹1200 for Dinner (split 3 ways: 400 each)
               Rahul owes Mohit 400, Ankit owes Mohit 400
    Expense 2: Rahul pays ₹600 for Taxi (split 3 ways: 200 each)
               Mohit owes Rahul 200, Ankit owes Rahul 200
    Net outcome:
      - Between Rahul & Mohit: Rahul owed 400 - 200 = Rahul owes Mohit 200
      - Between Ankit & Mohit: Ankit owes Mohit 400
      - Between Ankit & Rahul: Ankit owes Rahul 200
    """
    u1, u2, u3, g1 = setup_trip(client)

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
        "description": "Taxi"
    })

    res = client.get(f"/groups/{g1['id']}/balances")
    assert res.status_code == 200
    balances = res.json()

    assert balances["Rahul"]["owes"]["Mohit"] == 200.0
    assert balances["Ankit"]["owes"]["Mohit"] == 400.0
    assert balances["Ankit"]["owes"]["Rahul"] == 200.0


def test_detailed_balances_endpoint(client):
    u1, u2, u3, g1 = setup_trip(client)

    client.post("/expenses", json={
        "group_id": g1["id"],
        "paid_by": u1["id"],
        "amount": 1200.0,
        "description": "Dinner"
    })

    res = client.get("/balances/detailed")
    assert res.status_code == 200
    data = res.json()
    assert "balances" in data
    assert len(data["balances"]) == 2

    # Check debtor and creditor names
    debtors = {b["debtor_name"] for b in data["balances"]}
    creditors = {b["creditor_name"] for b in data["balances"]}
    assert debtors == {"Rahul", "Ankit"}
    assert creditors == {"Mohit"}
