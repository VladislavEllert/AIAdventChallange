"""Day 31: /help command — SSE flow via TestClient, mocked provider/MCP/RAG.
Zero live calls (no ProxyAPI, no Ollama, no MCP network)."""
import json
from unittest.mock import patch

from agent_web.services.rag.index import Chunk


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


def _fake_chunk(score_source="agent_web/services/rag/retriever.py"):
    return Chunk(
        chunk_id="c1", text="RAG retrieval code excerpt " * 10,
        embedding=[0.1] * 4, source=score_source, title="retriever.py",
        section="retriever.py", strategy="fixed",
    )


def test_help_no_args_lists_commands(client):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]

    r2 = client.post("/api/chat/stream", json={"session_id": sid, "message": "/help"})
    assert r2.status_code == 200
    events = _parse_sse(r2.text)
    assert events[0]["event"] == "chunk"
    assert "/mcp" in events[0]["data"]["text"]
    assert events[-1]["event"] == "done"


def test_help_with_question_sse_order_and_sources(client):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]

    fake_hits = [(_fake_chunk(), 0.9)]
    fake_meta = {"top_k_raw": 20, "top_k_kept": 1, "top_k_final": 1, "best_score": 0.9}

    with patch("agent_web.services.commands_help.get_rag_index", return_value=[]), \
         patch("agent_web.services.commands_help.rag_search", return_value=(fake_hits, dict(fake_meta))), \
         patch("agent_web.services.commands_help.get_tools_sync", return_value=[]), \
         patch("agent_web.services.commands_help.call_tool_sync", return_value="feature/day-31"):
        r2 = client.post("/api/chat/stream", json={
            "session_id": sid, "message": "/help как реализован RAG в этом проекте?"
        })

    assert r2.status_code == 200
    events = _parse_sse(r2.text)
    event_names = [e["event"] for e in events]

    # sources -> rag_meta -> chunk(s) -> ... -> done, in that order
    assert event_names[0] == "sources"
    assert event_names[1] == "rag_meta"
    assert "chunk" in event_names
    assert event_names[-1] == "done"
    assert event_names.index("sources") < event_names.index("rag_meta") < event_names.index("chunk")

    sources = events[event_names.index("sources")]["data"]
    assert len(sources) == 1
    assert sources[0]["source"] == "agent_web/services/rag/retriever.py"


def test_help_low_score_gives_dont_know_with_branch(client):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]

    with patch("agent_web.services.commands_help.get_rag_index", return_value=[]), \
         patch("agent_web.services.commands_help.rag_search", return_value=([], {"best_score": 0.0})), \
         patch("agent_web.services.commands_help.get_tools_sync", return_value=[]), \
         patch("agent_web.services.mcp_client._tool_registry", {"git_current_branch": "project"}), \
         patch("agent_web.services.commands_help.call_tool_sync", return_value="main"):
        r2 = client.post("/api/chat/stream", json={
            "session_id": sid, "message": "/help на какой я ветке?"
        })

    events = _parse_sse(r2.text)
    chunks = [e["data"]["text"] for e in events if e["event"] == "chunk"]
    full_text = "".join(chunks)
    assert "main" in full_text


def test_help_mcp_unreachable_degrades_gracefully(client):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]

    with patch("agent_web.services.commands_help.get_rag_index", return_value=[]), \
         patch("agent_web.services.commands_help.rag_search", return_value=([], {"best_score": 0.0})), \
         patch("agent_web.services.commands_help.get_tools_sync", side_effect=Exception("mcp down")):
        r2 = client.post("/api/chat/stream", json={
            "session_id": sid, "message": "/help на какой я ветке?"
        })

    assert r2.status_code == 200
    events = _parse_sse(r2.text)
    assert events[-1]["event"] == "done"
    chunks = "".join(e["data"]["text"] for e in events if e["event"] == "chunk")
    assert "недоступен" in chunks
