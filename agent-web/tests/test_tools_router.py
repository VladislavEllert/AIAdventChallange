"""Day 34: routers/tools.py — plain request/response endpoints, no SSE/threading
concerns (unlike chat.py's confirm flow, which is deliberately NOT tested
through TestClient — see plan's Tests table note)."""
from agent_web.services.tools import confirm


def test_list_tools_includes_fs_tools(client):
    resp = client.get("/api/tools")
    assert resp.status_code == 200
    names = {t["name"] for t in resp.json()["tools"]}
    assert {"read_file", "search_files", "list_dir", "write_file", "delete_file"} <= names


def test_list_tools_reports_danger_level(client):
    resp = client.get("/api/tools")
    by_name = {t["name"]: t["danger_level"] for t in resp.json()["tools"]}
    assert by_name["read_file"] == "safe"
    assert by_name["write_file"] == "dangerous"
    assert by_name["delete_file"] == "dangerous"


def test_confirm_unknown_call_id_returns_not_ok(client):
    resp = client.post("/api/tools/confirm", json={"call_id": "nope", "approved": True})
    assert resp.status_code == 200
    assert resp.json() == {"ok": False}


def test_confirm_resolves_pending_request(client):
    confirm.start_session("router-test-session")
    req = confirm.request_confirmation("router-test-session", "write_file", {"path": "x"}, "test")
    try:
        resp = client.post("/api/tools/confirm", json={"call_id": req.call_id, "approved": True})
        assert resp.json() == {"ok": True}
        assert req.event.is_set()
        assert req.approved is True
    finally:
        confirm.end_session("router-test-session")
        confirm._reset_for_tests()
