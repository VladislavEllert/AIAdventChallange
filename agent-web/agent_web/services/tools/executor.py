"""Day 34: tool executor — danger check -> optional human confirmation -> run.

Exceptions from `tool.execute(**arguments)` are ALWAYS caught here and turned
into a structured `{"ok": False, "result": "..."}` — a broken tool call must
never propagate a raw traceback into the chat SSE stream or crash the
generator (plan step 34.3).

Two entry points sharing the same core generator:
- `execute_stream(...)` — used by chat.py. Yields SSE-shaped events
  (`confirm_request`, `keepalive`, `confirm_result`, `tool_result`) so the
  caller can turn a long confirmation wait into real SSE frames.
- `execute(...)` — blocking convenience wrapper (drains the generator) for
  headless/unit-test callers that don't need SSE framing.
"""
from typing import Any, Iterator

from agent_web.services.tools import confirm, danger, registry


def execute_stream(
    tool_name: str,
    arguments: dict[str, Any],
    stream_id: str = "",
    reason: str = "",
    confirm_timeout: float = confirm.DEFAULT_TIMEOUT,
    confirm_poll_interval: float = confirm.DEFAULT_POLL_INTERVAL,
) -> Iterator[tuple[str, dict]]:
    tool = registry.get(tool_name)
    if tool is None:
        yield ("tool_result", {"ok": False, "denied": False, "result": f"Unknown tool '{tool_name}'"})
        return

    target_path = arguments.get("path", "") if isinstance(arguments, dict) else ""
    level = danger.danger_level(tool_name, target_path)

    if level == danger.DANGEROUS:
        req = confirm.request_confirmation(
            stream_id, tool_name, arguments,
            reason or f"'{tool_name}' modifies the filesystem and requires confirmation.",
        )
        yield ("confirm_request", {
            "call_id": req.call_id, "tool_name": tool_name,
            "arguments": arguments, "reason": req.reason,
        })

        approved = False
        for kind, payload in confirm.wait_for_confirmation(req.call_id, confirm_timeout, confirm_poll_interval):
            if kind == "keepalive":
                yield ("keepalive", {})
            else:
                approved = bool(payload)

        yield ("confirm_result", {"call_id": req.call_id, "approved": approved})

        if not approved:
            yield ("tool_result", {"ok": False, "denied": True, "result": "Operation denied by user (or confirmation timed out)."})
            return

        # A human clicking "Разрешить" on the confirm modal IS the real-write
        # authorization — that's the whole point of gating this tool behind
        # human-in-the-loop confirmation. Don't also require the LLM to have
        # remembered to pass dry_run=false in its own tool-call arguments: it
        # often omits the field entirely (defaults to dry_run=True), which
        # silently turned every approved write into a no-op preview — found
        # live, reproduced with a real browser click, not a hypothetical.
        if "dry_run" in arguments or tool_name == "write_file":
            arguments = {**arguments, "dry_run": False}

    try:
        result = tool.execute(**arguments)
        yield ("tool_result", {"ok": True, "denied": False, "result": result})
    except Exception as e:
        yield ("tool_result", {"ok": False, "denied": False, "result": f"Tool error: {e}"})


def execute(
    tool_name: str,
    arguments: dict[str, Any],
    stream_id: str = "",
    reason: str = "",
    confirm_timeout: float = confirm.DEFAULT_TIMEOUT,
    confirm_poll_interval: float = confirm.DEFAULT_POLL_INTERVAL,
) -> dict:
    """Blocking wrapper — drains execute_stream, returns only the final tool_result payload."""
    result = {"ok": False, "denied": False, "result": "no result produced"}
    for kind, payload in execute_stream(tool_name, arguments, stream_id, reason, confirm_timeout, confirm_poll_interval):
        if kind == "tool_result":
            result = payload
    return result
