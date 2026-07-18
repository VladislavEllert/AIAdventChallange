<!-- source: agent-web/agent_web/services/task_runner.py | title: task_runner.py -->

"""
TaskRunner: bridges synchronous TaskCoordinator with async FastAPI.

Thread runs TaskCoordinator.run().
output_fn → puts messages to asyncio.Queue via run_coroutine_threadsafe.
confirm_fn → blocks thread on threading.Event, set by POST /tasks/{id}/feedback.
"""
import asyncio
import threading
from typing import Any

from agent_cli.llm.provider import LLMProvider
from agent_cli.state.coordinator import TaskCoordinator, TaskState

# Global registry task_id → TaskRunner
_registry: dict[str, "TaskRunner"] = {}


def get_runner(task_id: str) -> "TaskRunner | None":
    return _registry.get(task_id)


def create_runner(
    task: TaskState,
    provider: LLMProvider,
    model: str = "",
    profile_content: str = "",
    invariants: list[str] | None = None,
) -> "TaskRunner":
    r = TaskRunner(task, provider, model, profile_content, invariants or [])
    _registry[task.task_id] = r
    return r


class TaskRunner:
    def __init__(
        self,
        task: TaskState,
        provider: LLMProvider,
        model: str,
        profile_content: str,
        invariants: list[str],
    ) -> None:
        self.task = task
        self.provider = provider
        self.model = model or task.model
        self.profile_content = profile_content
        self.invariants = invariants

        # Output log (catch-up for new SSE subscribers)
        self._log: list[dict[str, Any]] = []
        self._subscribers: list[asyncio.Queue] = []

        # Event loop reference set by start()
        self._loop: asyncio.AbstractEventLoop | None = None

        # Confirm bridge
        self._confirm_event = threading.Event()
        self._confirm_value: str | None = ""  # "" = continue, None = pause, non-empty = feedback

        # State
        self.done = False
        self.paused = False
        self.error: str | None = None
        self._thread: threading.Thread | None = None

    # ── public API ────────────────────────────────────────────────────────────

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"task-{self.task.task_id}")
        self._thread.start()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        # Send catch-up
        for msg in self._log:
            q.put_nowait(msg)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    def send_feedback(self, action: str, text: str = "") -> None:
        """Called from HTTP endpoint thread. Unblocks confirm_fn."""
        if action == "continue":
            self._confirm_value = ""
        elif action == "pause":
            self._confirm_value = None
        else:  # "feedback"
            self._confirm_value = text or ""
        self._confirm_event.set()

    # ── internals ─────────────────────────────────────────────────────────────

    def _emit(self, msg: dict) -> None:
        """Thread-safe emit to all subscribers."""
        self._log.append(msg)
        if self._loop is None:
            return
        for q in list(self._subscribers):
            asyncio.run_coroutine_threadsafe(q.put(msg), self._loop)

    def _output_fn(self, text: str) -> None:
        self._emit({"type": "output", "text": text})

    def _confirm_fn(self, prompt: str) -> str | None:
        """Blocks thread until send_feedback() is called."""
        self._emit({"type": "confirm", "prompt": prompt})
        self.paused = True
        self._confirm_event.wait()
        self._confirm_event.clear()
        self.paused = False
        return self._confirm_value

    def _run(self) -> None:
        try:
            coord = TaskCoordinator(
                provider=self.provider,
                model=self.model,
                profile_content=self.profile_content,
                invariants=self.invariants,
                interactive=True,
            )
            result = coord.run(
                self.task,
                output_fn=self._output_fn,
                confirm_fn=self._confirm_fn,
            )
            self.task = result
            self._emit({"type": "done", "stage": result.stage.value, "task": result.to_dict()})
        except Exception as exc:
            self.error = str(exc)
            self._emit({"type": "error", "text": str(exc)})
        finally:
            self.done = True
