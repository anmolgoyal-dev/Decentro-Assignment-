import pytest


def test_create_group_success(client):
    response = client.post("/groups", json={"name": "Goa Trip", "description": "Friends vacation"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Goa Trip"
    assert data["description"] == "Friends vacation"
    assert "id" in data


def test_list_groups(client):
    client.post("/groups", json={"name": "Goa Trip"})
    client.post("/groups", json={"name": "Roommates"})

    response = client.get("/groups")
    assert response.status_code == 200
    groups = response.json()
    assert len(groups) == 2


def test_add_member_to_group(client):
    u1 = client.post("/users", json={"name": "Mohit"}).json()
    g1 = client.post("/groups", json={"name": "Goa Trip"}).json()

    response = client.post(f"/groups/{g1['id']}/members", json={"user_id": u1["id"]})
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == u1["id"]
    assert data["name"] == "Mohit"


def test_add_duplicate_member(client):
    u1 = client.post("/users", json={"name": "Mohit"}).json()
    g1 = client.post("/groups", json={"name": "Goa Trip"}).json()

    client.post(f"/groups/{g1['id']}/members", json={"user_id": u1["id"]})
    res_dup = client.post(f"/groups/{g1['id']}/members", json={"user_id": u1["id"]})
    assert res_dup.status_code == 400
    assert "already a member" in res_dup.json()["detail"]


def test_add_member_invalid_user_or_group(client):
    u1 = client.post("/users", json={"name": "Mohit"}).json()
    g1 = client.post("/groups", json={"name": "Goa Trip"}).json()

    # Invalid group
    res1 = client.post("/groups/9999/members", json={"user_id": u1["id"]})
    assert res1.status_code == 404

    # Invalid user
    res2 = client.post(f"/groups/{g1['id']}/members", json={"user_id": 9999})
    assert res2.status_code == 404


def test_list_group_members(client):
    u1 = client.post("/users", json={"name": "Mohit"}).json()
    u2 = client.post("/users", json={"name": "Rahul"}).json()
    g1 = client.post("/groups", json={"name": "Goa Trip"}).json()

    client.post(f"/groups/{g1['id']}/members", json={"user_id": u1["id"]})
    client.post(f"/groups/{g1['id']}/members", json={"user_id": u2["id"]})

    res = client.get(f"/groups/{g1['id']}/members")
    assert res.status_code == 200
    members = res.json()
    assert len(members) == 2
    names = [m["name"] for m in members]
    assert "Mohit" in names
    assert "Rahul" in names
