"""Day 33: /support command — SSE flow via TestClient, mocked provider/MCP/RAG.
Zero live calls (no ProxyAPI, no Ollama, no MCP network).

Core acceptance check (plan's Tests table): get_ticket is mocked (as a real MCP tool
call, not a json import) and the ticket's environment/version fields must actually land
in the system message handed to the LLM provider — not just be fetched and discarded."""
import json
from unittest.mock import patch

from agent_web.services.rag.index import Chunk
from tests.conftest import MockProvider

_FAKE_TICKET = {
    "id": "TICKET-001",
    "title": "SOCKS proxy breaks local calls on Windows",
    "product_area": "local-llm",
    "version": "week-06 day-30 (Windows deploy)",
    "environment": "Windows 11, RTX 4060, системный SOCKS-прокси включён",
    "symptom": "Ollama/ComfyUI/MCP запросы виснут или падают через прокси",
    "steps": ["step1", "step2"],
    "status": "resolved",
    "user": "vladislav",
    "history": [{"author": "vladislav", "text": "Чат виснет на локальной модели"}],
}


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


def _fake_chunk():
    return Chunk(
        chunk_id="c1", text="FAQ: SOCKS proxy fix trust_env=False " * 5,
        embedding=[0.1] * 4, source="agent-web/data/rag/corpus_project/faq.md",
        title="faq.md", section="Локальные модели / прокси на Windows", strategy="fixed",
    )


def test_support_missing_args_shows_usage(client):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]

    r2 = client.post("/api/chat/stream", json={"session_id": sid, "message": "/support"})
    assert r2.status_code == 200
    events = _parse_sse(r2.text)
    full_text = "".join(e["data"]["text"] for e in events if e["event"] == "chunk")
    assert "Использование" in full_text
    assert events[-1]["event"] == "done"


def test_support_unknown_ticket_reports_error_no_crash(client):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]

    with patch("agent_web.services.commands_support.get_tools_sync", return_value=[]), \
         patch("agent_web.services.mcp_client._tool_registry", {"get_ticket": "project"}), \
         patch("agent_web.services.commands_support.call_tool_sync", return_value="Error: ticket 'TICKET-999' not found."):
        r2 = client.post("/api/chat/stream", json={
            "session_id": sid, "message": "/support TICKET-999 что случилось?"
        })

    assert r2.status_code == 200
    events = _parse_sse(r2.text)
    full_text = "".join(e["data"]["text"] for e in events if e["event"] == "chunk")
    assert "TICKET-999" in full_text
    assert events[-1]["event"] == "done"


def test_support_mcp_unreachable_degrades_gracefully(client):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]

    with patch("agent_web.services.commands_support.get_tools_sync", side_effect=Exception("mcp down")):
        r2 = client.post("/api/chat/stream", json={
            "session_id": sid, "message": "/support TICKET-001 как починить?"
        })

    assert r2.status_code == 200
    events = _parse_sse(r2.text)
    full_text = "".join(e["data"]["text"] for e in events if e["event"] == "chunk")
    assert "недоступен" in full_text
    assert events[-1]["event"] == "done"


def test_support_ticket_environment_and_version_land_in_system_message(client, monkeypatch):
    """The core day-33 acceptance check: environment/version from the (mocked) MCP
    get_ticket response must be present in the system message passed to the LLM."""
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]

    captured = {}

    def _spy_chat_stream_with_stats(self, messages, model, **kwargs):
        captured["messages"] = messages
        from tests.conftest import _Ref
        return (w + " " for w in "ответ по тикету".split()), _Ref()

    monkeypatch.setattr(MockProvider, "chat_stream_with_stats", _spy_chat_stream_with_stats)

    fake_hits = [(_fake_chunk(), 0.9)]
    fake_meta = {"top_k_raw": 20, "top_k_kept": 1, "top_k_final": 1, "best_score": 0.9}

    with patch("agent_web.services.commands_support.get_rag_index", return_value=[]), \
         patch("agent_web.services.commands_support.rag_search", return_value=(fake_hits, dict(fake_meta))), \
         patch("agent_web.services.commands_support.get_tools_sync", return_value=[]), \
         patch("agent_web.services.mcp_client._tool_registry", {"get_ticket": "project"}), \
         patch("agent_web.services.commands_support.call_tool_sync", return_value=json.dumps(_FAKE_TICKET)):
        r2 = client.post("/api/chat/stream", json={
            "session_id": sid,
            "message": "/support TICKET-001 как починить прокси на Windows?",
        })

    assert r2.status_code == 200
    events = _parse_sse(r2.text)
    assert events[-1]["event"] == "done"

    assert "messages" in captured, "provider was never called — ticket fetch must have short-circuited"
    system_content = captured["messages"][0]["content"]
    assert _FAKE_TICKET["environment"] in system_content
    assert _FAKE_TICKET["version"] in system_content
    assert _FAKE_TICKET["symptom"] in system_content
    assert "[КОНТЕКСТ ТИКЕТА]" in system_content


def test_support_sse_order_sources_before_chunk(client, monkeypatch):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]

    def _spy_chat_stream_with_stats(self, messages, model, **kwargs):
        from tests.conftest import _Ref
        return (w + " " for w in "ok".split()), _Ref()

    monkeypatch.setattr(MockProvider, "chat_stream_with_stats", _spy_chat_stream_with_stats)

    fake_hits = [(_fake_chunk(), 0.9)]
    fake_meta = {"top_k_raw": 20, "top_k_kept": 1, "top_k_final": 1, "best_score": 0.9}

    with patch("agent_web.services.commands_support.get_rag_index", return_value=[]), \
         patch("agent_web.services.commands_support.rag_search", return_value=(fake_hits, dict(fake_meta))), \
         patch("agent_web.services.commands_support.get_tools_sync", return_value=[]), \
         patch("agent_web.services.mcp_client._tool_registry", {"get_ticket": "project"}), \
         patch("agent_web.services.commands_support.call_tool_sync", return_value=json.dumps(_FAKE_TICKET)):
        r2 = client.post("/api/chat/stream", json={
            "session_id": sid, "message": "/support TICKET-001 вопрос"
        })

    events = _parse_sse(r2.text)
    event_names = [e["event"] for e in events]
    assert event_names[0] == "sources"
    assert event_names[1] == "rag_meta"
    assert "chunk" in event_names
    assert event_names[-1] == "done"
