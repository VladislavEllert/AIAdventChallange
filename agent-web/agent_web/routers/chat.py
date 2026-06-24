"""
Chat SSE streaming router.

After response:
1. check_code() — fast regex pre-check (no LLM cost)
2. check_llm()  — LLM-based thorough check (only if code check passes)
If violation → pop_last_exchange(), rollback stats, emit 'violation' event.
"""
import json
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from agent_web.dependencies import get_manager
from agent_web.services.agent_manager import AgentManager
from agent_web.schemas.chat import ChatRequest
from agent_cli.invariants.store import load_invariants
from agent_cli.invariants.checker import check_code, check_llm
import agent_cli.config as cfg
from agent_web.services.mcp_client import get_tools_sync, call_tool_sync, TOOL_LABELS

router = APIRouter(tags=["chat"])


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _load_invariant_strings() -> list[str]:
    """Load invariants from store, normalize to plain strings."""
    result: list[str] = []
    try:
        for item in load_invariants():
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                result.extend(str(v) for v in item.values())
    except Exception:
        pass
    return result


def _load_profile_content(profile_name: str) -> str:
    """Read profile markdown content. Returns empty string on failure."""
    try:
        path = Path(cfg.PROFILES_DIR) / f"{profile_name}.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except Exception:
        return ""


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, manager: AgentManager = Depends(get_manager)):
    # Load fresh invariants on every request (user may have added via InvariantsPanel)
    invariants = _load_invariant_strings()

    # Load profile content
    profile_content = _load_profile_content(req.profile_name) if req.profile_name else ""

    # Get or create agent, applying current request params
    agent = manager.get_or_create(
        req.session_id,
        persona=req.persona or "",
        model=req.model or "",
        profile_content=profile_content,
    )

    # Always sync fresh invariants + profile into existing agent instance
    agent.invariants = invariants
    if profile_content:
        agent.profile_content = profile_content
    if req.model:
        agent.model = req.model

    def generate():
        # ── MCP tool calling ──────────────────────────────────────────────
        tool_used = False
        usage = None

        try:
            tool_schemas = get_tools_sync()
        except Exception:
            tool_schemas = []

        if tool_schemas:
            try:
                agent._try_summarize()
                all_messages = agent._build_messages(req.message)
                tool_response = agent.provider.client.chat.completions.create(
                    model=agent.model,
                    messages=all_messages,
                    tools=tool_schemas,
                    tool_choice="auto",
                )
                choice = tool_response.choices[0]

                if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                    tool_used = True
                    extra_messages = list(all_messages)
                    # Append assistant message with tool_calls
                    extra_messages.append({
                        "role": "assistant",
                        "content": choice.message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in choice.message.tool_calls
                        ],
                    })

                    for tc in choice.message.tool_calls:
                        name = tc.function.name
                        args = json.loads(tc.function.arguments or "{}")
                        label = TOOL_LABELS.get(name, f"⚙️ {name}...")

                        yield _sse_event("tool_start", {"name": name, "label": label})
                        try:
                            result = call_tool_sync(name, args)
                        except Exception as e:
                            result = f"Tool error: {e}"
                        yield _sse_event("tool_done", {"name": name, "result_preview": result[:100]})

                        extra_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result,
                        })

                    # Stream final response with tool results in context
                    chunk_iter2, ref2 = agent.provider.chat_stream_with_stats(
                        extra_messages, agent.model
                    )
                    full_response = ""
                    for chunk in chunk_iter2:
                        full_response += chunk
                        yield _sse_event("chunk", {"text": chunk})

                    agent.memory.add_message("user", req.message)
                    agent.memory.add_message("assistant", full_response)
                    usage = ref2.usage
                    agent.session_stats.add(usage)
            except Exception:
                # Tools failed — fall through to normal response
                tool_used = False
        # ─────────────────────────────────────────────────────────────────

        if not tool_used:
            chunk_iter, ref = agent.respond_stream_with_stats(req.message)
            for chunk in chunk_iter:
                yield _sse_event("chunk", {"text": chunk})
            usage = ref.usage

        # ── Invariant check ───────────────────────────────────────────────
        if invariants:
            # Get the response that was just added to memory
            response_text = (
                agent.memory.short_term[-1]["content"]
                if agent.memory.short_term and agent.memory.short_term[-1]["role"] == "assistant"
                else ""
            )

            ok, violation_desc = check_code(response_text, invariants)
            if ok:
                # Deeper LLM check (synchronous — runs in Starlette thread pool)
                ok, violation_desc = check_llm(
                    response_text, invariants, manager.provider, agent.model
                )

            if not ok:
                # Rollback: remove last exchange from memory
                agent.memory.pop_last_exchange()
                # Rollback stats
                agent.session_stats.cost_rub -= usage.cost_rub
                agent.session_stats.prompt_tokens -= usage.prompt_tokens
                agent.session_stats.completion_tokens -= usage.completion_tokens
                agent.session_stats.calls = max(0, agent.session_stats.calls - 1)

                yield _sse_event("violation", {
                    "invariant": violation_desc,
                    "description": violation_desc,
                })
                yield _sse_event("done", {})
                return
        # ─────────────────────────────────────────────────────────────────

        yield _sse_event("usage", {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "cost_rub": round(usage.cost_rub, 6),
            "elapsed_ms": usage.elapsed_ms,
        })

        manager.save(req.session_id)
        yield _sse_event("done", {})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
