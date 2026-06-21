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
from agent_cli.state.swarm import SwarmRunner

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
        chat_summary: str = "",
    ) -> None:
        self.provider = provider
        self.profile_content = profile_content
        self.invariants = invariants or []
        self.model = model
        self.interactive = interactive
        self.swarm = SwarmRunner(
            provider=provider,
            model=model,
            profile_content=profile_content,
            chat_summary=chat_summary,
        )

    def _agent(self, stage: Stage) -> Agent:
        return Agent(
            provider=self.provider,
            persona=STAGE_PERSONAS[stage],
            model=self.model,
            profile_content=self.profile_content,
            invariants=self.invariants,
        )

    def _run_planning(
        self,
        task: "TaskState",
        output_fn: Callable[[str], None],
        retry_count: int,
        user_feedback: str = "",
    ) -> tuple[str, int]:
        """
        Рой → синтез → проверка плана.
        Возвращает (plan, retry_count).
        user_feedback — замечания пользователя, инжектируются в синтез.
        Если оркестратор отклоняет план — повторяем рой (до MAX_RETRIES).
        """
        for attempt in range(MAX_RETRIES):
            swarm_results = self.swarm.run_swarm(task.request, output_fn)
            plan = self.swarm.synthesize_plan(
                task.request, swarm_results, output_fn, user_feedback=user_feedback
            )
            ok, comment = self.swarm.check_plan(task.request, plan, output_fn)
            if ok:
                output_fn("\n── [УТВЕРЖДЁННЫЙ ПЛАН] ──")
                output_fn(plan)
                return plan, retry_count
            retry_count += 1
            output_fn(f"\n[Оркестратор] План требует доработки: {comment}")
            output_fn(f"[!] Повтор планирования ({attempt + 1}/{MAX_RETRIES})...")
            if retry_count >= MAX_RETRIES:
                output_fn(f"[!] Лимит попыток планирования достигнут. Берём последний план.")
                return plan, retry_count
        return plan, retry_count  # pragma: no cover

    def run(
        self,
        task: TaskState,
        output_fn: Callable[[str], None] = print,
        confirm_fn: Callable[[str], str | None] | None = None,
    ) -> TaskState:
        """
        confirm_fn возвращает:
          ""   — продолжить
          None — приостановить задачу
          str  — фидбек пользователя → перезапустить текущую стадию с поправками
        """
        retry_count = 0
        user_feedback = ""
        _first_iter = True
        _prev_stage: dict[Stage, Stage] = {
            Stage.EXECUTION: Stage.PLANNING,
            Stage.VALIDATION: Stage.EXECUTION,
        }

        while task.stage != Stage.DONE:
            stage = task.stage

            # На resume: пауза ПЕРЕД стадией (первая итерация, не старт с нуля)
            if _first_iter and stage != Stage.PLANNING and self.interactive and confirm_fn:
                result = confirm_fn(f"\nПродолжить → [{stage.value}]?")
                _first_iter = False
                if result is None:
                    output_fn("Задача приостановлена. /task resume — продолжить.")
                    return task
                elif result:
                    user_feedback = result
                    task.stage = _prev_stage.get(stage, stage)
                    task.save()
                    continue
            _first_iter = False

            # ── PLANNING: рой + оркестратор ──────────────────────────────────
            if stage == Stage.PLANNING:
                plan, retry_count = self._run_planning(
                    task, output_fn, retry_count, user_feedback=user_feedback
                )
                user_feedback = ""
                task.plan = plan
                task.stage = Stage.EXECUTION
                task.save()

            # ── EXECUTION: агент + проверка оркестратора ──────────────────────
            elif stage == Stage.EXECUTION:
                val_feedback = ""
                if task.validation_result and VALIDATION_FAIL_MARKER in task.validation_result:
                    val_feedback = f"\n\nФидбек от валидации:\n{task.validation_result}"
                user_fb_block = f"\n\nПоправки пользователя:\n{user_feedback}" if user_feedback else ""
                user_feedback = ""
                prompt = f"Задача: {task.request}\n\nПлан:\n{task.plan}{val_feedback}{user_fb_block}"

                output_fn(f"\n── [EXECUTION] ──")
                agent = self._agent(Stage.EXECUTION)
                response = agent.respond(prompt)
                output_fn(response)
                task.execution_result = response

                ok, comment = self.swarm.check_execution(
                    task.request, task.plan, response, output_fn
                )
                if not ok:
                    retry_count += 1
                    output_fn(f"\n[Оркестратор] Выполнение не соответствует плану: {comment}")
                    if retry_count > MAX_RETRIES:
                        output_fn(f"[!] Достигнут лимит попыток ({MAX_RETRIES}). Задача остановлена.")
                        task.save()
                        return task
                    output_fn(f"[!] Повтор выполнения ({retry_count}/{MAX_RETRIES})...")
                    task.save()
                    continue

                task.stage = Stage.VALIDATION
                task.save()

            # ── VALIDATION: агент + финальный вердикт ─────────────────────────
            else:  # VALIDATION
                prompt = (
                    f"Задача: {task.request}\n\n"
                    f"План:\n{task.plan}\n\n"
                    f"Результат выполнения:\n{task.execution_result}"
                )
                output_fn(f"\n── [VALIDATION] ──")
                agent = self._agent(Stage.VALIDATION)
                response = agent.respond(prompt)
                output_fn(response)
                task.validation_result = response

                done, comment = self.swarm.final_verdict(
                    task.request, task.plan, response, output_fn
                )
                if done:
                    task.stage = Stage.DONE
                else:
                    retry_count += 1
                    output_fn(f"\n[Оркестратор] Задача требует доработки: {comment}")
                    if retry_count > MAX_RETRIES:
                        output_fn(f"[!] Достигнут лимит попыток ({MAX_RETRIES}). Задача остановлена.")
                        task.stage = Stage.EXECUTION
                        task.save()
                        return task
                    task.stage = Stage.EXECUTION

                task.save()

            # ── пауза между стадиями ──────────────────────────────────────────
            if task.stage != Stage.DONE and self.interactive and confirm_fn:
                result = confirm_fn(f"\nПродолжить → [{task.stage.value}]?")
                if result is None:
                    output_fn("Задача приостановлена. /task resume — продолжить.")
                    return task
                elif result:
                    # фидбек пользователя → перезапустить предыдущую стадию
                    output_fn(f"[↩] Возврат к [{stage.value}] с поправками пользователя...")
                    user_feedback = result
                    task.stage = stage
                    task.save()

        output_fn("\n── [DONE] Задача завершена. ──")
        return task
