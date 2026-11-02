import pytest


def test_create_user_success(client):
    response = client.post("/users", json={"name": "Mohit", "email": "mohit@example.com"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Mohit"
    assert data["email"] == "mohit@example.com"
    assert "id" in data


def test_create_user_without_email(client):
    response = client.post("/users", json={"name": "Rahul"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Rahul"
    assert data["email"] is None


def test_create_user_duplicate_email(client):
    client.post("/users", json={"name": "Mohit", "email": "mohit@example.com"})
    response = client.post("/users", json={"name": "Mohit Duplicate", "email": "mohit@example.com"})
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_list_users(client):
    client.post("/users", json={"name": "Mohit"})
    client.post("/users", json={"name": "Rahul"})
    client.post("/users", json={"name": "Ankit"})

    response = client.get("/users")
    assert response.status_code == 200
    users = response.json()
    assert len(users) == 3
    names = [u["name"] for u in users]
    assert "Mohit" in names
    assert "Rahul" in names
    assert "Ankit" in names


def test_get_user_by_id(client):
    create_res = client.post("/users", json={"name": "Mohit"})
    user_id = create_res.json()["id"]

    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Mohit"


def test_get_user_not_found(client):
    response = client.get("/users/9999")
    assert response.status_code == 404
