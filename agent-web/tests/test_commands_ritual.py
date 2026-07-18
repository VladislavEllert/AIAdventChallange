"""Day 35: /ritual command — SSE flow via TestClient, mocked provider.
Zero live calls. Only covers --dry-run and the usage/rejection paths here —
the full write+confirm+commit path is covered by test_tools_executor.py
(shared executor machinery) + the live Playwright e2e (week-07/day-35/screens/)
per the plan's "confirm (SSE)" test note: TestClient's single blocking ASGI
portal makes a second concurrent confirm POST during a stream flaky in pytest,
real end-to-end belongs in Playwright, same reasoning as day 34's tests."""
import json

from tests.conftest import MockProvider


def _parse_sse(text: str) -> list[dict]:
    events = []
    event = ""
    for line in text.strip().split("\n"):
        if line.startswith("event: "):
            event = line[7:].strip()
        elif line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                events.append({"event": event, "data": data})
                event = ""
            except json.JSONDecodeError:
                pass
    return events


def test_ritual_missing_args_shows_usage(client):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]

    r2 = client.post("/api/chat/stream", json={"session_id": sid, "message": "/ritual"})
    assert r2.status_code == 200
    events = _parse_sse(r2.text)
    full_text = "".join(e["data"]["text"] for e in events if e["event"] == "chunk")
    assert "Использование" in full_text
    assert events[-1]["event"] == "done"


def test_ritual_dry_run_shows_diff_and_does_not_write(client, tmp_path):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]

    r2 = client.post(
        "/api/chat/stream",
        json={"session_id": sid, "message": "/ritual day 99 --dry-run"},
    )
    assert r2.status_code == 200
    events = _parse_sse(r2.text)
    full_text = "".join(e["data"]["text"] for e in events if e["event"] == "chunk")

    # Default MockProvider response ("Mock response") is not a valid table row,
    # so the verifier rejects it — assert the rejection path surfaces cleanly
    # and no confirm/write ever happens (no confirm_request event at all).
    assert "Верификатор" in full_text
    assert not any(e["event"] == "confirm_request" for e in events)
    assert events[-1]["event"] == "done"


def test_ritual_dry_run_with_valid_draft_shows_patch_diff_no_confirm(tmp_path):
    """Uses a custom mock provider whose canned response IS a valid row, to
    exercise the approved-draft + --dry-run path (diff shown, nothing written,
    no confirm handshake triggered)."""
    from fastapi.testclient import TestClient
    from agent_web.app import create_app
    from agent_web.dependencies import get_session_store, get_manager
    from agent_web.services.agent_manager import AgentManager
    from agent_cli.core.sessions import SessionStore

    row = "| 07 | 99 | ritual test | done | [week-07/day-99](week-07/day-99/) | todo |"
    provider = MockProvider(response=row)
    db_path = str(tmp_path / "test_sessions.db")
    store = SessionStore(db_path)
    manager = AgentManager(provider, store)

    app = create_app()
    app.dependency_overrides[get_session_store] = lambda: store
    app.dependency_overrides[get_manager] = lambda: manager
    c = TestClient(app)
    try:
        r = c.post("/api/sessions", json={})
        sid = r.json()["session_id"]
        r2 = c.post(
            "/api/chat/stream",
            json={"session_id": sid, "message": "/ritual day 99 --dry-run"},
        )
        assert r2.status_code == 200
        events = _parse_sse(r2.text)
        full_text = "".join(e["data"]["text"] for e in events if e["event"] == "chunk")

        assert "Верификатор одобрил" in full_text
        assert "--dry-run" in full_text
        assert not any(e["event"] == "confirm_request" for e in events)
        assert events[-1]["event"] == "done"
    finally:
        app.dependency_overrides.clear()
