<!-- source: agent-web/agent_web/services/commands_help.py | title: commands_help.py -->

"""`/help` — day 31.

No args: lists available commands (this registry + the legacy 4 in chat.py,
documented statically since they aren't in the registry).

With a question: forces kb="project" RAG (never the handbook — this command
is about the project itself), forces RAG on regardless of req.use_rag, and
injects the real current git branch via the local project MCP server so the
model never guesses it.

`kb` is resolved here, server-side — it is NOT a ChatRequest field. A request
field with no UI toggle is a dead surface (plan's explicit call).
"""
from typing import Iterator

from agent_web.dependencies import get_rag_index
from agent_web.services.commands import register
from agent_web.services.mcp_client import call_tool_sync, get_tools_sync
from agent_web.services.rag.config import KNOWLEDGE_BASES, THRESHOLD
from agent_web.services.rag.retriever import search as rag_search

_KB = "project"

# Static — legacy commands (chat.py) aren't in the registry (see commands.py docstring),
# so /help lists them by hand. Keep in sync if a legacy command's syntax changes.
_LEGACY_COMMANDS: list[tuple[str, str]] = [
    ("/mcp", "Список доступных MCP-инструментов и серверов."),
    ("/history TICKER [minutes]", "История котировки из SQLite (VPS MCP)."),
    ("/ping TICKER [interval]", "Живой стрим котировки, 10 замеров."),
    ("/analyze SYMBOL [interval]", "3-шаговый анализ крипты: свечи → индикаторы → отчёт."),
]


_UNREACHABLE_MSG = "неизвестно (project MCP-сервер недоступен — запусти mcp-server/project_server.py)"


def _current_branch() -> str:
    try:
        # call_tool_sync routes by name via a registry populated by get_tools_sync() —
        # must refresh it first. If the project server is down, get_tools_sync()
        # silently drops it (per-server try/except) and _tool_registry falls back
        # to routing the name at another server, which replies "unknown tool" as
        # normal text (not an exception) — check the registry explicitly instead
        # of letting that misrouted reply masquerade as a branch name.
        from agent_web.services.mcp_client import _tool_registry
        get_tools_sync()
        if _tool_registry.get("git_current_branch") != "project":
            return _UNREACHABLE_MSG
        result = call_tool_sync("git_current_branch", {})
        result = (result or "").strip()
        return result if result else "неизвестно (пустой ответ от project MCP-сервера)"
    except Exception:
        return _UNREACHABLE_MSG


def _gen_kwargs(model: str) -> dict:
    """Mirrors chat.py's _text_gen_kwargs. Duplicated (not imported) to avoid a circular
    import — chat.py imports this module to register /help at startup."""
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


def handle_help(msg: str, req, agent, manager) -> Iterator[tuple[str, dict]]:
    parts = msg.strip().split(maxsplit=1)
    question = parts[1].strip() if len(parts) > 1 else ""

    if not question:
        lines = ["**📖 Доступные команды**\n\n"]
        lines.append("• `/help <вопрос>` — спросить про этот проект (RAG по коду/докам + текущая git-ветка)\n")
        for name, desc in _LEGACY_COMMANDS:
            lines.append(f"• `{name}` — {desc}\n")
        yield "chunk", {"text": "".join(lines)}
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

    branch = _current_branch()

    if rag_meta["best_score"] < kb_cfg["threshold_answer"]:
        text = (
            f"Не нашёл релевантного в базе знаний проекта ({kb_cfg['label']}). "
            f"Попробуй переформулировать вопрос.\n\nТекущая git-ветка: **{branch}**."
        )
        agent.memory.add_message("user", msg)
        agent.memory.add_message("assistant", text)
        yield "chunk", {"text": text}
        manager.save(req.session_id)
        yield "done", {}
        return

    context_parts = []
    for i, (chunk, score) in enumerate(hits, 1):
        context_parts.append(
            f"[{i}] score={score:.3f} | {chunk.source} | {chunk.section}\n{chunk.text[:700]}"
        )
    context_block = "\n\n---\n".join(context_parts)

    system_suffix = (
        "\n\n[HELP MODE] Отвечай ТОЛЬКО на основе приведённых excerpts из кода/документации "
        "этого проекта. В конце добавь раздел '**Источники:**' со списком путей файлов, "
        "которые использовал.\n"
        f"[ТЕКУЩАЯ GIT-ВЕТКА] {branch} — если пользователь спрашивает про ветку, отвечай "
        "этим значением, а не выдумывай."
    )
    agent._try_summarize()
    messages = agent._build_messages(
        question, working_context=f"Project knowledge base excerpts:\n\n{context_block}"
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


register("/help", "Справка по командам; с вопросом — RAG по проекту + текущая git-ветка.", handle_help)
