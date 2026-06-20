import json
import os
import uuid
from pathlib import Path
from typing import Callable

import agent_cli.config as cfg
from agent_cli.core.agent import Agent
from agent_cli.llm.provider import LLMProvider
from agent_cli.state.machine import (
    Stage,
    STAGE_PERSONAS,
    VALIDATION_OK_MARKER,
    VALIDATION_FAIL_MARKER,
)

MAX_RETRIES = 3


class TaskState:
    def __init__(self, task_id: str, request: str) -> None:
        self.task_id = task_id
        self.request = request
        self.stage = Stage.PLANNING
        self.plan: str = ""
        self.execution_result: str = ""
        self.validation_result: str = ""
        self.profile_name: str = ""
        self.model: str = cfg.DEFAULT_MODEL

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "request": self.request,
            "stage": self.stage.value,
            "plan": self.plan,
            "execution_result": self.execution_result,
            "validation_result": self.validation_result,
            "profile_name": self.profile_name,
            "model": self.model,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TaskState":
        ts = cls(d["task_id"], d["request"])
        ts.stage = Stage(d["stage"])
        ts.plan = d.get("plan", "")
        ts.execution_result = d.get("execution_result", "")
        ts.validation_result = d.get("validation_result", "")
        ts.profile_name = d.get("profile_name", "")
        ts.model = d.get("model", cfg.DEFAULT_MODEL)
        return ts

    def save(self) -> None:
        path = Path(cfg.TASKS_DIR) / f"{self.task_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, task_id: str) -> "TaskState":
        path = Path(cfg.TASKS_DIR) / f"{task_id}.json"
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    @classmethod
    def latest(cls) -> "TaskState | None":
        d = Path(cfg.TASKS_DIR)
        if not d.exists():
            return None
        files = sorted(d.glob("*.json"), key=os.path.getmtime, reverse=True)
        return cls.load(files[0].stem) if files else None

    @classmethod
    def new(cls, request: str) -> "TaskState":
        return cls(uuid.uuid4().hex[:8], request)


class TaskCoordinator:
    def __init__(
        self,
        provider: LLMProvider,
        profile_content: str = "",
        invariants: list[str] | None = None,
        model: str = cfg.DEFAULT_MODEL,
        interactive: bool = True,
    ) -> None:
        self.provider = provider
        self.profile_content = profile_content
        self.invariants = invariants or []
        self.model = model
        self.interactive = interactive

    def _agent(self, stage: Stage) -> Agent:
        return Agent(
            provider=self.provider,
            persona=STAGE_PERSONAS[stage],
            model=self.model,
            profile_content=self.profile_content,
            invariants=self.invariants,
        )

    def run(
        self,
        task: TaskState,
        output_fn: Callable[[str], None] = print,
        confirm_fn: Callable[[str], bool] | None = None,
    ) -> TaskState:
        retry_count = 0

        while task.stage != Stage.DONE:
            stage = task.stage
            agent = self._agent(stage)

            if stage == Stage.PLANNING:
                prompt = f"Задача: {task.request}"
            elif stage == Stage.EXECUTION:
                feedback = ""
                if task.validation_result and VALIDATION_FAIL_MARKER in task.validation_result:
                    feedback = f"\n\nФидбек от валидации:\n{task.validation_result}"
                prompt = f"Задача: {task.request}\n\nПлан:\n{task.plan}{feedback}"
            else:  # VALIDATION
                prompt = (
                    f"Задача: {task.request}\n\n"
                    f"План:\n{task.plan}\n\n"
                    f"Результат выполнения:\n{task.execution_result}"
                )

            output_fn(f"\n── [{stage.value.upper()}] ──")
            response = agent.respond(prompt)
            output_fn(response)

            if stage == Stage.PLANNING:
                task.plan = response
                next_stage = Stage.EXECUTION
            elif stage == Stage.EXECUTION:
                task.execution_result = response
                next_stage = Stage.VALIDATION
            else:  # VALIDATION
                task.validation_result = response
                if VALIDATION_OK_MARKER in response:
                    next_stage = Stage.DONE
                else:
                    retry_count += 1
                    if retry_count > MAX_RETRIES:
                        output_fn(f"\n[!] Достигнут лимит попыток ({MAX_RETRIES}). Задача остановлена.")
                        task.stage = Stage.EXECUTION  # leave resumable
                        task.save()
                        return task
                    next_stage = Stage.EXECUTION

            task.stage = next_stage
            task.save()

            if self.interactive and next_stage != Stage.DONE and confirm_fn:
                if not confirm_fn(f"\nПродолжить → [{next_stage.value}]?"):
                    output_fn("Задача приостановлена. /task resume — продолжить.")
                    return task

        output_fn("\n── [DONE] Задача завершена. ──")
        return task
