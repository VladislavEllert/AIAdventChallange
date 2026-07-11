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


# ── owner isolation (light per-nickname session isolation, no auth) ─────────

def test_create_session_stores_owner(client):
    r = client.post("/api/sessions", json={"name": "alice-session", "owner": "alice"})
    assert r.json()["owner"] == "alice"


def test_list_sessions_filters_by_owner(client):
    client.post("/api/sessions", json={"name": "a1", "owner": "alice"})
    client.post("/api/sessions", json={"name": "b1", "owner": "bob"})

    r_alice = client.get("/api/sessions", params={"owner": "alice"})
    names_alice = [s["name"] for s in r_alice.json()]
    assert "a1" in names_alice
    assert "b1" not in names_alice

    r_bob = client.get("/api/sessions", params={"owner": "bob"})
    names_bob = [s["name"] for s in r_bob.json()]
    assert "b1" in names_bob
    assert "a1" not in names_bob


def test_legacy_ownerless_sessions_visible_to_everyone(client):
    # Session created without an owner (e.g. pre-migration data) should still
    # show up for any nickname, not silently vanish.
    client.post("/api/sessions", json={"name": "legacy"})
    r = client.get("/api/sessions", params={"owner": "anyone"})
    names = [s["name"] for s in r.json()]
    assert "legacy" in names
