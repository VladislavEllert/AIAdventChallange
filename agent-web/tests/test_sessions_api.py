import pytest


def test_list_sessions_empty(client):
    r = client.get("/api/sessions")
    assert r.status_code == 200
    assert r.json() == []


def test_create_session(client):
    r = client.post("/api/sessions", json={"name": "my-session"})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "my-session"
    assert data["display_name"] == "my-session"
    assert "session_id" in data


def test_list_sessions_after_create(client):
    client.post("/api/sessions", json={"name": "s1"})
    client.post("/api/sessions", json={"name": "s2"})
    r = client.get("/api/sessions")
    assert r.status_code == 200
    names = [s["name"] for s in r.json()]
    assert "s1" in names
    assert "s2" in names


def test_get_session(client):
    r = client.post("/api/sessions", json={"name": "test-get"})
    sid = r.json()["session_id"]

    r2 = client.get(f"/api/sessions/{sid}")
    assert r2.status_code == 200
    assert r2.json()["session_id"] == sid
    assert r2.json()["messages"] == []


def test_get_session_not_found(client):
    r = client.get("/api/sessions/nonexistent")
    assert r.status_code == 404


def test_rename_session(client):
    r = client.post("/api/sessions", json={"name": "old-name"})
    sid = r.json()["session_id"]

    r2 = client.put(f"/api/sessions/{sid}", json={"name": "new-name"})
    assert r2.status_code == 200

    r3 = client.get(f"/api/sessions/{sid}")
    assert r3.json()["name"] == "new-name"


def test_delete_session(client):
    r = client.post("/api/sessions", json={"name": "to-delete"})
    sid = r.json()["session_id"]

    r2 = client.delete(f"/api/sessions/{sid}")
    assert r2.status_code == 200

    r3 = client.get(f"/api/sessions/{sid}")
    assert r3.status_code == 404


def test_delete_not_found(client):
    r = client.delete("/api/sessions/ghost")
    assert r.status_code == 404


def test_session_has_no_name_uses_id(client):
    r = client.post("/api/sessions", json={})
    data = r.json()
    assert data["display_name"] == data["session_id"]
