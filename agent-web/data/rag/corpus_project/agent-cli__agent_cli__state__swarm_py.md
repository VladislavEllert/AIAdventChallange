<!-- source: agent-cli/agent_cli/state/swarm.py | title: swarm.py -->

"""
SwarmRunner — рой агентов для стадии PLANNING + Оркестратор-надсмотрщик.

Архитектура вызовов:
  PLANNING:   run_swarm (×3)  → synthesize_plan (×1) → check_plan (×1)
  EXECUTION:  check_execution (×1)
  VALIDATION: final_verdict (×1)
"""
from __future__ import annotations

from typing import Callable

from agent_cli.core.agent import Agent
from agent_cli.llm.provider import LLMProvider
from agent_cli.state.machine import (
    ORCHESTRATOR_APPROVE,
    ORCHESTRATOR_DONE,
    ORCHESTRATOR_PERSONA,
    PLANNING_SWARM,
    PLAN_MARKER,
)
import agent_cli.config as cfg


OutputFn = Callable[[str], None]


class SwarmRunner:
    """
    Управляет роем агентов на стадии PLANNING и оркестратором на всех стадиях.
    """

    def __init__(
        self,
        provider: LLMProvider,
        model: str = cfg.DEFAULT_MODEL,
        profile_content: str = "",
        chat_summary: str = "",
    ) -> None:
        self.provider = provider
        self.model = model
        self.profile_content = profile_content
        self.chat_summary = chat_summary  # summary из основного чата — только оркестратору

    # ── вспомогательные ──────────────────────────────────────────────────────

    def _make_agent(self, persona: str) -> Agent:
        """Создаёт одноразового агента с нужной персоной."""
        return Agent(
            provider=self.provider,
            persona=persona,
            model=self.model,
            profile_content=self.profile_content,
        )

    def _orchestrator(self) -> Agent:
        """Оркестратор — получает профиль + chat_summary через working_context в respond()."""
        return Agent(
            provider=self.provider,
            persona=ORCHESTRATOR_PERSONA,
            model=self.model,
            profile_content=self.profile_content,
        )

    def _orc_context(self) -> str:
        """Префикс с summary основного чата для оркестратора (если есть)."""
        if self.chat_summary:
            return f"[Контекст диалога с пользователем]\n{self.chat_summary}\n\n"
        return ""

    # ── рой (PLANNING) ───────────────────────────────────────────────────────

    def run_swarm(self, task_request: str, output_fn: OutputFn) -> list[tuple[str, str]]:
        """
        Запускает 3 агента роя последовательно.
        Каждый следующий агент видит ответы предыдущих — дополняет, не повторяет.
        Возвращает [(name, response), ...].
        """
        results: list[tuple[str, str]] = []
        for name, persona in PLANNING_SWARM:
            output_fn(f"\n── [PLANNING / {name.upper()}] ──")
            agent = self._make_agent(persona)

            if results:
                prev_block = "\n\n".join(
                    f"[{n}]:\n{r}" for n, r in results
                )
                prompt = (
                    f"Задача: {task_request}\n\n"
                    f"Коллеги уже высказались:\n{prev_block}\n\n"
                    f"Твоя роль — {name}. Дополни их, не повторяй сказанное."
                )
            else:
                prompt = f"Задача: {task_request}"

            response = agent.respond(prompt)
            output_fn(response)
            results.append((name, response))
        return results

    def synthesize_plan(
        self,
        task_request: str,
        swarm_results: list[tuple[str, str]],
        output_fn: OutputFn,
        user_feedback: str = "",
    ) -> str:
        """
        Оркестратор синтезирует мнения роя в единый план.
        Возвращает текст плана (должен содержать PLAN_MARKER).
        """
        expert_block = "\n\n".join(
            f"=== Мнение: {name} ===\n{resp}" for name, resp in swarm_results
        )
        feedback_block = (
            f"\n\nПоправки пользователя к предыдущему плану:\n{user_feedback}"
            if user_feedback else ""
        )
        prompt = (
            f"{self._orc_context()}"
            f"Режим: СИНТЕЗ-ПЛАНА\n\n"
            f"Задача пользователя: {task_request}\n\n"
            f"Мнения экспертов:\n{expert_block}{feedback_block}\n\n"
            f"Синтезируй в один чёткий план. Заверши маркером {PLAN_MARKER}."
        )
        output_fn("\n── [ОРКЕСТРАТОР / СИНТЕЗ ПЛАНА] ──")
        orc = self._orchestrator()
        plan = orc.respond(prompt)
        output_fn(plan)
        # Страховка: если маркер не вставлен, добавляем
        if PLAN_MARKER not in plan:
            plan += f"\n\n{PLAN_MARKER}"
        return plan

    def check_plan(
        self,
        task_request: str,
        plan: str,
        output_fn: OutputFn,
    ) -> tuple[bool, str]:
        """
        Оркестратор проверяет план перед исполнением.
        Возвращает (ok, comment).
        """
        prompt = (
            f"{self._orc_context()}"
            f"Режим: ПРОВЕРКА-ПЛАНА\n\n"
            f"Задача пользователя: {task_request}\n\n"
            f"План:\n{plan}\n\n"
            "Ответь строго одной строкой: APPROVE или REWORK:<причина>"
        )
        output_fn("\n── [ОРКЕСТРАТОР / ПРОВЕРКА ПЛАНА] ──")
        orc = self._orchestrator()
        verdict = orc.respond(prompt).strip()
        output_fn(verdict)
        ok = verdict.upper().startswith(ORCHESTRATOR_APPROVE)
        comment = verdict[len(ORCHESTRATOR_APPROVE) + 1:].strip() if not ok else ""
        return ok, comment

    # ── после EXECUTION ───────────────────────────────────────────────────────

    def check_execution(
        self,
        task_request: str,
        plan: str,
        execution_result: str,
        output_fn: OutputFn,
    ) -> tuple[bool, str]:
        """
        Оркестратор проверяет соответствие результата выполнения плану.
        Возвращает (ok, comment).
        """
        prompt = (
            f"{self._orc_context()}"
            f"Режим: ПРОВЕРКА-ВЫПОЛНЕНИЯ\n\n"
            f"Задача пользователя: {task_request}\n\n"
            f"Утверждённый план (приоритет над исходным запросом):\n{plan}\n\n"
            f"Результат выполнения:\n{execution_result}\n\n"
            "Проверь: результат соответствует УТВЕРЖДЁННОМУ ПЛАНУ (не исходному запросу если они расходятся). "
            "Ответь строго одной строкой: APPROVE или REWORK:<что конкретно не так>"
        )
        output_fn("\n── [ОРКЕСТРАТОР / ПРОВЕРКА ВЫПОЛНЕНИЯ] ──")
        orc = self._orchestrator()
        verdict = orc.respond(prompt).strip()
        output_fn(verdict)
        ok = verdict.upper().startswith(ORCHESTRATOR_APPROVE)
        comment = verdict[len(ORCHESTRATOR_APPROVE) + 1:].strip() if not ok else ""
        return ok, comment

    # ── после VALIDATION ──────────────────────────────────────────────────────

    def final_verdict(
        self,
        task_request: str,
        plan: str,
        validation_result: str,
        output_fn: OutputFn,
    ) -> tuple[bool, str]:
        """
        Оркестратор выносит финальный вердикт.
        Возвращает (done, comment).
        """
        prompt = (
            f"{self._orc_context()}"
            f"Режим: ФИНАЛЬНЫЙ-ВЕРДИКТ\n\n"
            f"Задача пользователя: {task_request}\n\n"
            f"Утверждённый план:\n{plan}\n\n"
            f"Результат валидации:\n{validation_result}\n\n"
            "Ответь строго одной строкой: DONE или RETRY:<что нужно переделать>"
        )
        output_fn("\n── [ОРКЕСТРАТОР / ФИНАЛЬНЫЙ ВЕРДИКТ] ──")
        orc = self._orchestrator()
        verdict = orc.respond(prompt).strip()
        output_fn(verdict)
        done = verdict.upper().startswith(ORCHESTRATOR_DONE)
        comment = verdict[len(ORCHESTRATOR_DONE) + 1:].strip() if not done else ""
        return done, comment
