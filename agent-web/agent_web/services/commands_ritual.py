"""`/ritual day <NN> [--dry-run]` — day 35.

Runs the day_report.py chain (collect -> draft -> verify -> build_patch),
shows the diff in chat, then — unless `--dry-run` — stages the write_file
DANGEROUS confirm handshake (day 34's `tools/executor.py`) for each touched
file, and finally `git_commit` (also DANGEROUS). Nothing is written or
committed without the human clicking Allow on the SAME `ConfirmToolModal`
day 34 built — this command reuses that infra directly rather than building
a parallel one.

The writer LLM call is FORCED to `rituals.day_report.MODEL`
(`openai/gpt-4o-mini`) regardless of `agent.model` — CLAUDE.md's week-7 model
constraint pins every live ritual call to that model, not whatever the user
has selected for chat.
"""
from typing import Iterator

from agent_web.services.commands import register
from agent_web.services.rituals import day_report
from agent_web.services.tools import executor as tools_executor
from agent_web.services.tools import git_tools as _git_tools  # noqa: F401 — registers git_commit
from agent_web.services.tools.fs_tools import REPO_ROOT

_USAGE = "Использование: `/ritual day <NN> [--dry-run]`, например `/ritual day 35`"


def _chat_fn_factory(agent):
    def _chat_fn(messages: list[dict], model: str) -> str:
        text, _ref = agent.provider.chat_with_stats(messages, model, max_tokens=800, temperature=0.2)
        return text
    return _chat_fn


def _drain_dangerous(tool_name: str, arguments: dict, stream_id: str) -> Iterator[tuple[str, dict]]:
    """Runs one DANGEROUS tool through executor.execute_stream, forwarding
    confirm_request/confirm_result verbatim (frontend's ConfirmToolModal is
    generic — no tool-name coupling, see day-34's ConfirmToolModal.tsx) and
    swallowing keepalive (chat.py's command dispatch wraps every yielded
    event in its normal SSE framing, not the raw inert `: keepalive\\n\\n`
    comment line the tool-calling loop uses — simplest to just not forward
    it rather than reproduce that exact format here)."""
    result = None
    for kind, payload in tools_executor.execute_stream(tool_name, arguments, stream_id=stream_id):
        if kind == "keepalive":
            continue
        if kind in ("confirm_request", "confirm_result"):
            yield kind, payload
        elif kind == "tool_result":
            result = payload
    yield "_result", result or {"ok": False, "denied": False, "result": "no result produced"}


def handle_ritual(msg: str, req, agent, manager, stream_id: str = "") -> Iterator[tuple[str, dict]]:
    parts = msg.strip().split()
    # parts[0] == "/ritual"
    dry_run = "--dry-run" in parts
    parts = [p for p in parts if p != "--dry-run"]

    if len(parts) < 3 or parts[1].lower() != "day":
        yield "chunk", {"text": _USAGE}
        yield "done", {}
        return

    day = parts[2].strip().zfill(2)

    yield "chunk", {"text": f"🔁 Ритуал: собираю изменения для дня {day}...\n\n"}

    result = day_report.run_ritual(
        REPO_ROOT, "07", day, chat_fn=_chat_fn_factory(agent), model=day_report.MODEL,
    )

    yield "chunk", {"text": f"**Черновик строки:**\n```\n{result.row}\n```\n\n"}

    if not result.verify_result.ok:
        errs = "\n".join(f"- {e}" for e in result.verify_result.errors)
        text = f"❌ Верификатор отклонил черновик:\n{errs}\n\nНичего не записано."
        agent.memory.add_message("user", msg)
        agent.memory.add_message("assistant", text)
        yield "chunk", {"text": text}
        manager.save(req.session_id)
        yield "done", {}
        return

    diff_text = result.patch.diff_text or "(нет изменений — содержимое не поменялось)"
    yield "chunk", {"text": f"✅ Верификатор одобрил. Патч:\n```diff\n{diff_text}\n```\n"}

    if dry_run:
        text = "\n[--dry-run] Патч не применён, коммит не сделан."
        agent.memory.add_message("user", msg)
        agent.memory.add_message("assistant", text)
        yield "chunk", {"text": text}
        manager.save(req.session_id)
        yield "done", {}
        return

    written: list[str] = []
    for rel, content in result.patch.files.items():
        last = None
        for kind, payload in _drain_dangerous(
            "write_file", {"path": rel, "content": content, "dry_run": False}, stream_id,
        ):
            if kind == "_result":
                last = payload
            else:
                yield kind, payload
        if not last or not last.get("ok"):
            text = f"\n❌ Запись `{rel}` отклонена или не удалась: {last.get('result') if last else '?'}"
            agent.memory.add_message("user", msg)
            agent.memory.add_message("assistant", text)
            yield "chunk", {"text": text}
            manager.save(req.session_id)
            yield "done", {}
            return
        written.append(rel)
        yield "chunk", {"text": f"\n✏️ Записано: `{rel}`"}

    commit_msg = f"docs(week-07): ritual progress-line for day {day}"
    last = None
    for kind, payload in _drain_dangerous(
        "git_commit", {"message": commit_msg, "paths": written}, stream_id,
    ):
        if kind == "_result":
            last = payload
        else:
            yield kind, payload

    if not last or not last.get("ok"):
        text = f"\n❌ Коммит отклонён или не удался: {last.get('result') if last else '?'}"
    else:
        text = f"\n✅ Закоммичено локально: {last.get('result')}\n\nPush не выполнялся — вручную, по политике."

    agent.memory.add_message("user", msg)
    agent.memory.add_message("assistant", text)
    yield "chunk", {"text": text}
    manager.save(req.session_id)
    yield "done", {}


register(
    "/ritual",
    "Ритуал курса: `/ritual day <NN> [--dry-run]` — черновик строки прогресса + патч README/progress.md, коммит только после подтверждения.",
    handle_ritual,
)
