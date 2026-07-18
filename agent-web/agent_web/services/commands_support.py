"""`/support <ticket_id> <question>` — day 33.

Pulls the ticket record through the project MCP server's `get_ticket` tool (a real
MCP round-trip — NOT a direct `json.load` of tickets.json from this process; the plan
is explicit that the ticket must arrive through the MCP tool, same reasoning as /help's
git branch in day 31: the model must not guess or the code must not silently bypass the
tool boundary). The ticket's fields (environment, version, symptom, steps, history) are
injected into the system prompt as a `[КОНТЕКСТ ТИКЕТА]` block, then RAG(kb=project)
answers the actual question grounded in that context plus the project corpus (including
`corpus_project/faq.md`, day 33.2) so the answer cites relevant FAQ/docs instead of
giving generic advice.

Mirrors commands_help.py's shape (kb resolved server-side, not a ChatRequest field;
rewrite_to_english off for kb=project; same SSE event order: sources -> rag_meta -> chunk*
-> usage -> done).
"""
from typing import Iterator

from agent_web.dependencies import get_rag_index
from agent_web.services.commands import register
from agent_web.services.mcp_client import call_tool_sync, get_tools_sync
from agent_web.services.rag.config import KNOWLEDGE_BASES, THRESHOLD
from agent_web.services.rag.retriever import search as rag_search

_KB = "project"

_USAGE = "Использование: `/support <ticket_id> <вопрос>`, например `/support TICKET-001 как починить прокси на Windows?`"


def _fetch_ticket(ticket_id: str) -> dict | str:
    """Returns the ticket dict on success, or a human-readable error string.
    Routes through the MCP tool registry the same way commands_help._current_branch()
    does — check the registry explicitly rather than trusting a misrouted "unknown tool"
    reply from another server to masquerade as ticket data."""
    try:
        from agent_web.services.mcp_client import _tool_registry
        get_tools_sync()
        if _tool_registry.get("get_ticket") != "project":
            return "project MCP-сервер недоступен (запусти mcp-server/project_server.py)"
        raw = call_tool_sync("get_ticket", {"id": ticket_id})
    except Exception as e:
        return f"project MCP-сервер недоступен: {e}"

    if not raw or not raw.strip():
        return "пустой ответ от project MCP-сервера"
    if raw.strip().startswith("Error:"):
        return raw.strip()

    import json
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return f"не удалось разобрать ответ MCP-сервера: {raw[:200]}"


def _ticket_context_block(ticket: dict) -> str:
    history = ticket.get("history") or []
    history_lines = "\n".join(
        f"  - {h.get('author', '?')}: {h.get('text', '')}" for h in history
    )
    steps = ticket.get("steps") or []
    steps_lines = "\n".join(f"  {i}. {s}" for i, s in enumerate(steps, 1))
    return (
        f"id: {ticket.get('id')}\n"
        f"title: {ticket.get('title')}\n"
        f"product_area: {ticket.get('product_area')}\n"
        f"version: {ticket.get('version')}\n"
        f"environment: {ticket.get('environment')}\n"
        f"symptom: {ticket.get('symptom')}\n"
        f"status: {ticket.get('status')}\n"
        f"steps:\n{steps_lines}\n"
        f"history:\n{history_lines}"
    )


def _gen_kwargs(model: str) -> dict:
    """Duplicated from commands_help.py (same anti-circular-import reasoning: chat.py
    imports this module to register /support at startup)."""
    from agent_web.services.settings_store import load_settings
    s = load_settings()
    kwargs = {
        "temperature": s.get("temperature", 0.7),
        "max_tokens": s.get("max_tokens", 2048),
        "top_p": s.get("top_p", 1.0),
    }
    if model.startswith("ollama/"):
        kwargs["extra_body"] = {"options": {"num_ctx": s.get("num_ctx", 4096)}}
    return kwargs


def handle_support(msg: str, req, agent, manager, stream_id: str = "") -> Iterator[tuple[str, dict]]:
    # stream_id unused here — only day-35's /ritual needs it (git_commit confirm
    # handshake); accepted for signature compatibility with chat.py's dispatch call.
    parts = msg.strip().split(maxsplit=2)
    # parts[0] == "/support"
    if len(parts) < 3:
        yield "chunk", {"text": _USAGE}
        yield "done", {}
        return

    ticket_id, question = parts[1], parts[2].strip()
    ticket = _fetch_ticket(ticket_id)

    if isinstance(ticket, str):
        text = f"Не удалось получить тикет `{ticket_id}`: {ticket}"
        agent.memory.add_message("user", msg)
        agent.memory.add_message("assistant", text)
        yield "chunk", {"text": text}
        manager.save(req.session_id)
        yield "done", {}
        return

    kb_cfg = KNOWLEDGE_BASES[_KB]
    index = get_rag_index(kb=_KB)
    hits, rag_meta = rag_search(
        question, index, top_k=5, threshold=THRESHOLD, backend=kb_cfg["backend"]
    )
    rag_meta["kb"] = _KB

    sources_payload = [
        {
            "source": chunk.source,
            "section": chunk.section,
            "chunk_id": chunk.chunk_id,
            "quote": chunk.text[:300],
            "score": round(score, 4),
        }
        for chunk, score in hits
    ]
    yield "sources", sources_payload
    yield "rag_meta", rag_meta

    ticket_block = _ticket_context_block(ticket)
    context_parts = []
    for i, (chunk, score) in enumerate(hits, 1):
        context_parts.append(
            f"[{i}] score={score:.3f} | {chunk.source} | {chunk.section}\n{chunk.text[:700]}"
        )
    rag_context_block = "\n\n---\n".join(context_parts) if context_parts else "(нет релевантных документов)"

    system_suffix = (
        "\n\n[SUPPORT MODE] Ты отвечаешь на вопрос по конкретному тикету поддержки. "
        "ОБЯЗАТЕЛЬНО учитывай поля тикета ниже (особенно environment и version) — "
        "ответ должен быть специфичен для ЭТОЙ среды, а не общим советом. "
        "Используй excerpts из базы знаний проекта (включая FAQ) как источник решений, "
        "и завершай ответ разделом '**Источники:**' со списком путей файлов, которые "
        "использовал.\n"
        f"[КОНТЕКСТ ТИКЕТА]\n{ticket_block}"
    )

    agent._try_summarize()
    messages = agent._build_messages(
        question, working_context=f"Project knowledge base excerpts:\n\n{rag_context_block}"
    )
    messages[0] = {**messages[0], "content": messages[0]["content"] + system_suffix}

    chunk_iter, ref = agent.provider.chat_stream_with_stats(
        messages, agent.model, **_gen_kwargs(agent.model)
    )
    full_response = ""
    for chunk in chunk_iter:
        full_response += chunk
        yield "chunk", {"text": chunk}
    agent.memory.add_message("user", msg)
    agent.memory.add_message("assistant", full_response)
    usage = ref.usage
    agent.session_stats.add(usage)

    yield "usage", {
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
        "cost_rub": round(usage.cost_rub, 6),
        "elapsed_ms": usage.elapsed_ms,
    }
    manager.save(req.session_id)
    yield "done", {}


register(
    "/support",
    "Поддержка по тикету: `/support <ticket_id> <вопрос>` — контекст тикета через MCP + RAG по проекту.",
    handle_support,
)
