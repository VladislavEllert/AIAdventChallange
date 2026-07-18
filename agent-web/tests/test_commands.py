"""Day 31: slash-command registry — new commands resolve, unknown text doesn't
intercept, and the 4 legacy hardcoded commands in chat.py still dispatch
(regression — the new registry check sits BEFORE them in generate())."""
from unittest.mock import patch

from agent_web.services import commands


def test_resolve_registers_and_finds_new_command():
    def handler(msg, req, agent, manager):
        yield "chunk", {"text": "handled"}
        yield "done", {}

    commands.register("/zzz-test", "test command", handler)
    try:
        cmd = commands.resolve("/zzz-test some args")
        assert cmd is not None
        assert cmd.name == "/zzz-test"
        events = list(cmd.handler("/zzz-test some args", None, None, None))
        assert events[0] == ("chunk", {"text": "handled"})
    finally:
        commands._REGISTRY.pop("/zzz-test", None)


def test_resolve_unknown_command_returns_none():
    assert commands.resolve("/does-not-exist") is None


def test_resolve_plain_text_not_intercepted():
    assert commands.resolve("hello there") is None


def test_resolve_empty_string():
    assert commands.resolve("") is None


def test_help_is_registered_on_chat_import():
    # Importing chat.py (which imports commands_help for its registration side
    # effect) must have populated the registry with /help.
    import agent_web.routers.chat  # noqa: F401

    assert commands.resolve("/help") is not None
    assert commands.resolve("/help какой-то вопрос") is not None


# ── Legacy command regression: /mcp, /history, /ping, /analyze still dispatch ──
# through chat.py's own hardcoded branches, unaffected by the new registry check
# that now runs before them.

def test_legacy_mcp_still_dispatches(client):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]
    with patch("agent_web.routers.chat.get_tools_sync", return_value=[]):
        r2 = client.post("/api/chat/stream", json={"session_id": sid, "message": "/mcp"})
    assert r2.status_code == 200
    assert "MCP Tools" in r2.text


def test_legacy_history_still_dispatches(client):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]
    with patch("agent_web.routers.chat.call_tool_sync", return_value="fake history"):
        r2 = client.post("/api/chat/stream", json={"session_id": sid, "message": "/history SBER"})
    assert r2.status_code == 200
    assert "fake history" in r2.text


def test_legacy_ping_still_dispatches(client):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]
    with patch("agent_web.routers.chat.call_tool_sync", return_value="100.0"), \
         patch("time.sleep", return_value=None):
        r2 = client.post("/api/chat/stream", json={"session_id": sid, "message": "/ping SBER 1"})
    assert r2.status_code == 200
    assert "мониторинг" in r2.text


def test_legacy_analyze_still_dispatches(client):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]
    with patch("agent_web.routers.chat.call_tool_sync", return_value='{"error":"no data"}'):
        r2 = client.post("/api/chat/stream", json={"session_id": sid, "message": "/analyze BTCUSDT"})
    assert r2.status_code == 200
    assert "Анализ" in r2.text
