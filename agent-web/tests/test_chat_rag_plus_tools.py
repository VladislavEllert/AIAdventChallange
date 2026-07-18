"""Day 34.1 regression test: RAG + tool-calling must NOT be mutually exclusive.

Before the fix, chat.py's RAG branch (`if req.use_rag:`) always `return`ed
after streaming, so the tool-calling loop below it was unreachable whenever
`use_rag=True` — even if `use_mcp=True` was also requested. This test proves
the tool-calling loop is actually reached (a second LLM call happens, past
the RAG-only rewrite call) when both flags are set, while the old pure-RAG
fast path (`use_rag=True, use_mcp=False`) stays a single-call early return —
that fast path is covered by test_rag_rewrite.py's existing regression test
and is intentionally NOT re-asserted with call counts here to avoid
duplicating that coverage.
"""
from unittest.mock import MagicMock, patch

from agent_web.services.rag.index import Chunk


def _fake_hit():
    return (
        Chunk(chunk_id="c1", text="excerpt " * 20, embedding=[0.1] * 4,
              source="src.md", title="t", section="s", strategy="fixed"),
        0.9,
    )


def test_rag_and_mcp_both_on_reaches_tool_loop(client, mock_provider):
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]

    llm_client = MagicMock()
    llm_client.chat.completions.create.side_effect = [
        # 1st call: day-23 query rewrite (RAG branch)
        MagicMock(choices=[MagicMock(message=MagicMock(content="rewritten query"))]),
        # 2nd call: tool-calling round — no tool_calls, so the loop streams a
        # final answer via MockProvider.chat_stream_with_stats immediately.
        # Reaching THIS call at all is the regression signal — it never
        # happened pre-fix because the RAG branch always returned first.
        MagicMock(choices=[MagicMock(
            finish_reason="stop",
            message=MagicMock(tool_calls=None, content="final"),
        )]),
    ]
    mock_provider.client_for = MagicMock(return_value=(llm_client, "gpt-4o-mini"))

    with patch("agent_web.routers.chat.get_rag_index", return_value=[_fake_hit()[0]]), \
         patch("agent_web.routers.chat.rag_search", return_value=([_fake_hit()], {"best_score": 0.9})), \
         patch("agent_web.routers.chat.get_tools_sync", return_value=[]):
        resp = client.post("/api/chat/stream", json={
            "session_id": sid, "message": "what is RAG", "use_rag": True, "use_mcp": True,
        })

    assert resp.status_code == 200
    # Rewrite call + tool-loop call: proves the loop was reached past the RAG branch.
    assert llm_client.chat.completions.create.call_count == 2
    # The response body actually contains MockProvider's streamed text (split
    # across "chunk" SSE events, word by word), i.e. the tool loop's
    # "no tool_calls -> stream final answer" branch really ran.
    assert "event: chunk" in resp.text
    assert "Mock" in resp.text and "response" in resp.text


def test_rag_only_no_mcp_stays_single_call_fast_path(client, mock_provider):
    """Regression guard for the fast path the plan requires to stay intact:
    use_rag=True, use_mcp=False must still be the pre-day-34 single-call
    RAG-only behavior (no tool-loop LLM call at all)."""
    r = client.post("/api/sessions", json={})
    sid = r.json()["session_id"]

    llm_client = MagicMock()
    llm_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="rewritten query"))]
    )
    mock_provider.client_for = MagicMock(return_value=(llm_client, "gpt-4o-mini"))

    with patch("agent_web.routers.chat.get_rag_index", return_value=[_fake_hit()[0]]), \
         patch("agent_web.routers.chat.rag_search", return_value=([_fake_hit()], {"best_score": 0.9})):
        resp = client.post("/api/chat/stream", json={
            "session_id": sid, "message": "what is RAG", "use_rag": True, "use_mcp": False,
        })

    assert resp.status_code == 200
    # Only the rewrite call — no tool-loop call ever made.
    assert llm_client.chat.completions.create.call_count == 1
