"""Day 31: query-rewrite call count — kb=project (rewrite_to_english=False) never
calls the rewrite LLM; kb=handbook (rewrite_to_english=True) does, for
non-ollama models. Rewrite is day-23 functionality, only present on the
req.use_rag=True path in chat.py — /help (kb=project) has no rewrite call at
all in its implementation, which is what we're asserting here."""
from unittest.mock import MagicMock, patch

from agent_web.services.rag.index import Chunk


def _fake_hit():
    return (
        Chunk(chunk_id="c1", text="excerpt " * 20, embedding=[0.1] * 4,
              source="src.md", title="t", section="s", strategy="fixed"),
        0.9,
    )


def test_handbook_rag_path_calls_rewrite(client, mock_provider):
    """req.use_rag=True (kb=handbook, hardcoded in chat.py) — rewrite IS called
    for non-ollama models (day 23 behavior, unchanged by day 31)."""
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]

    rewrite_client = MagicMock()
    rewrite_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="rewritten query"))]
    )
    mock_provider.client_for = MagicMock(return_value=(rewrite_client, "gpt-4o-mini"))

    with patch("agent_web.routers.chat.get_rag_index", return_value=[_fake_hit()[0]]), \
         patch("agent_web.routers.chat.rag_search", return_value=([_fake_hit()], {"best_score": 0.9})):
        client.post("/api/chat/stream", json={
            "session_id": sid, "message": "what is RAG", "use_rag": True,
        })

    assert rewrite_client.chat.completions.create.call_count > 0


def test_help_project_kb_never_calls_rewrite(client, mock_provider):
    """/help (kb=project, rewrite_to_english=False) must never call the rewrite
    LLM — the project corpus is Russian+code, translating the query would hurt
    retrieval (plan 31.11)."""
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]

    rewrite_client = MagicMock()
    mock_provider.client_for = MagicMock(return_value=(rewrite_client, "gpt-4o-mini"))

    with patch("agent_web.services.commands_help.get_rag_index", return_value=[_fake_hit()[0]]), \
         patch("agent_web.services.commands_help.rag_search", return_value=([_fake_hit()], {"best_score": 0.9})), \
         patch("agent_web.services.commands_help.get_tools_sync", return_value=[]), \
         patch("agent_web.services.commands_help.call_tool_sync", return_value="main"):
        client.post("/api/chat/stream", json={
            "session_id": sid, "message": "/help как реализован RAG?",
        })

    assert rewrite_client.chat.completions.create.call_count == 0
