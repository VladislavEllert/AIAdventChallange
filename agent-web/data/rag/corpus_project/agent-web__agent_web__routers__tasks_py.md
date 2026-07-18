<!-- source: agent-web/agent_web/routers/tasks.py | title: tasks.py -->

"""
Task FSM router.

POST   /api/tasks              — create & start task
GET    /api/tasks/{id}         — status
GET    /api/tasks/{id}/stream  — SSE output stream
POST   /api/tasks/{id}/feedback — continue / pause / feedback
GET    /api/tasks              — list recent tasks
"""
import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent_web.dependencies import get_manager
from agent_web.services.agent_manager import AgentManager
from agent_web.services import task_runner as runner_mod
from agent_web.services.settings_store import load_settings
from agent_cli.state.coordinator import TaskState
from agent_cli.invariants.store import load_invariants

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    request: str
    model: str = ""
    profile_content: str = ""


class FeedbackBody(BaseModel):
    action: str   # "continue" | "pause" | "feedback"
    text: str = ""


def _invariants_list() -> list[str]:
    try:
        raw = load_invariants()
        result = []
        for item in raw:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                result.extend(item.values())
        return result
    except Exception:
        return []


@router.post("")
async def create_task(
    body: TaskCreate,
    manager: AgentManager = Depends(get_manager),
):
    settings = load_settings()
    model = body.model or settings.get("default_model", "ollama/qwen3:4b")

    task = TaskState.new(body.request)
    task.model = model
    task.save()

    runner = runner_mod.create_runner(
        task=task,
        provider=manager.provider,
        model=model,
        profile_content=body.profile_content,
        invariants=_invariants_list(),
    )
    loop = asyncio.get_event_loop()
    runner.start(loop)

    return {
        "task_id": task.task_id,
        "stage": task.stage.value,
        "request": task.request,
    }


@router.get("")
def list_tasks():
    """Return all in-memory runners (active tasks)."""
    return [
        {
            "task_id": r.task.task_id,
            "stage": r.task.stage.value,
            "request": r.task.request,
            "done": r.done,
            "paused": r.paused,
            "error": r.error,
        }
        for r in runner_mod._registry.values()
    ]


@router.get("/{task_id}")
def get_task(task_id: str):
    r = runner_mod.get_runner(task_id)
    if r:
        return {
            **r.task.to_dict(),
            "done": r.done,
            "paused": r.paused,
            "error": r.error,
            "log_count": len(r._log),
        }
    # Try loading from saved file
    try:
        task = TaskState.load(task_id)
        return {**task.to_dict(), "done": True, "paused": False, "error": None}
    except Exception:
        raise HTTPException(404, f"Task {task_id!r} not found")


@router.get("/{task_id}/stream")
async def stream_task(task_id: str):
    r = runner_mod.get_runner(task_id)
    if not r:
        raise HTTPException(404, f"Task {task_id!r} not found or not running")

    async def generate():
        q = r.subscribe()
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                    if msg["type"] in ("done", "error"):
                        break
                except asyncio.TimeoutError:
                    # Keepalive ping
                    yield "event: ping\ndata: {}\n\n"
                    if r.done:
                        break
        finally:
            r.unsubscribe(q)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{task_id}/feedback")
def task_feedback(task_id: str, body: FeedbackBody):
    r = runner_mod.get_runner(task_id)
    if not r:
        raise HTTPException(404, f"Task {task_id!r} not found")
    if r.done:
        raise HTTPException(400, "Task already done")
    r.send_feedback(body.action, body.text)
    return {"ok": True}
