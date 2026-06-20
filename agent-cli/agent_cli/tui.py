from __future__ import annotations

import os
from typing import Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from agent_cli.config import DEFAULT_MODEL
from agent_cli.core.memory import MAX_SHORT_TERM
from agent_cli.llm.provider import TokenUsage
from agent_cli.core.agent import Agent
from agent_cli.invariants.checker import check_llm
from agent_cli.invariants.store import add_invariant, load_invariants
from agent_cli.llm.proxyapi import ProxyAPIProvider
from agent_cli.profile.profile import UserProfile
from agent_cli.state.coordinator import TaskCoordinator, TaskState
from agent_cli.state.machine import Stage

console = Console()

_COMMANDS = [
    "/help", "/model", "/clear", "/exit",
    "/profile", "/profile show", "/profile list", "/profile switch", "/profile edit", "/profile create",
    "/task", "/task start", "/task resume",
    "/state",
    "/invariants", "/invariants list", "/invariants add",
]
_COMPLETER = WordCompleter(_COMMANDS, sentence=True)
_STYLE = Style.from_dict({"bottom-toolbar": "bg:#1e1e1e #666666"})


class TUI:
    def __init__(self) -> None:
        self.provider = ProxyAPIProvider()
        self.model: str = DEFAULT_MODEL
        self.current_profile: UserProfile | None = None
        self.invariants: list[str] = []
        self.agent: Agent = self._make_agent()
        self.current_task: TaskState | None = None
        self.session: PromptSession | None = None

    def _make_agent(self) -> Agent:
        profile_content = self.current_profile.to_prompt_text() if self.current_profile else ""
        return Agent(
            provider=self.provider,
            model=self.model,
            profile_content=profile_content,
            invariants=self.invariants,
        )

    def _toolbar(self) -> HTML:
        profile = self.current_profile.name if self.current_profile else "no profile"
        stage = self.current_task.stage.value if self.current_task else "—"
        stats = self.agent.session_stats
        cost_str = f"{stats.cost_rub:.4f}₽" if stats.calls else "0₽"
        tok_str = f"{stats.total_tokens}tok" if stats.calls else "0tok"
        ctx = f"{self.agent.memory.ctx_used}/{MAX_SHORT_TERM}"
        return HTML(
            f"<b>model:</b> {self.model}  "
            f"<b>profile:</b> {profile}  "
            f"<b>stage:</b> {stage}  "
            f"<b>ctx:</b> {ctx}  "
            f"<b>session:</b> {tok_str} / {cost_str}"
        )

    def _prompt(self, text: str) -> str:
        """Use session prompt if available, else fallback to input()."""
        if self.session:
            return self.session.prompt(text)
        return input(text)

    # ── profile handlers ──────────────────────────────────────────────────────

    def _handle_profile(self, args: list[str]) -> None:
        sub = args[0] if args else "show"

        if sub == "show":
            if not self.current_profile:
                console.print("[yellow]Профиль не выбран. /profile switch <name>[/]")
            else:
                console.print(
                    Panel(self.current_profile.to_prompt_text(), title=f"Профиль: {self.current_profile.name}")
                )

        elif sub == "list":
            profiles = UserProfile.list_all()
            console.print("Профили: " + (", ".join(profiles) or "[нет]"))

        elif sub == "switch":
            name = args[1] if len(args) > 1 else ""
            if not name:
                profiles = UserProfile.list_all()
                console.print("Доступны: " + ", ".join(profiles))
                name = self._prompt("Имя профиля: ").strip()
            if not name:
                return
            try:
                self.current_profile = UserProfile.load(name)
                self.agent = self._make_agent()
                console.print(f"[green]✓ Профиль: {name}[/]")
            except FileNotFoundError:
                console.print(f"[red]Профиль '{name}' не найден[/]")

        elif sub == "edit":
            if not self.current_profile:
                console.print("[yellow]Сначала выбери профиль: /profile switch[/]")
                return
            p = os.path.join(os.path.dirname(__file__), "..", "data", "profiles", f"{self.current_profile.name}.md")
            editor = os.environ.get("EDITOR", "open")
            os.system(f'{editor} "{os.path.abspath(p)}"')
            console.print("[dim]После сохранения сделай /profile switch, чтобы перезагрузить.[/]")

        elif sub == "create":
            self._profile_onboard(args[1] if len(args) > 1 else "")

        else:
            console.print(f"[red]Неизвестный подкоманд: {sub}[/]")

    def _profile_onboard(self, name: str = "") -> None:
        """Interactive profile builder: 4 questions → auto-route facts → save."""
        from agent_cli.profile.extractor import route_fact

        console.print(Panel(
            "Отвечай на 4 вопроса — я сам разложу ответы по нужным слоям профиля.",
            title="[cyan]Создание профиля[/cyan]",
        ))

        if not name:
            name = self._prompt("Имя профиля (латиницей, без пробелов): ").strip()
        if not name:
            console.print("[red]Имя обязательно[/]")
            return

        questions = [
            ("Кто ты? Чем занимаешься, какая у тебя роль?", "persona"),
            ("Как ты хочешь чтобы я с тобой общался? (кратко/развёрнуто, на ты/вы, строго/дружелюбно)", "style"),
            ("Что строго запрещено? (темы, инструменты, стиль которые не хочешь видеть)", "rules"),
            ("Твой технический стек: языки, фреймворки, инструменты", "stack"),
        ]

        profile = UserProfile(name=name)
        layers: dict[str, list[str]] = {k: [] for k in ("persona", "style", "rules", "stack", "interests")}

        for question, hint_layer in questions:
            console.print(f"\n[bold cyan]?[/bold cyan] {question}")
            answer = self._prompt("  ▶ ").strip()
            if not answer:
                continue
            # Auto-route: ask LLM which layer, fallback to hint
            detected = route_fact(answer, self.provider, self.model)
            target = detected if detected != "persona" or hint_layer == "persona" else hint_layer
            layers[target].append(answer)
            console.print(f"  [dim]→ слой: {target}[/dim]")

        profile.persona = " ".join(layers["persona"])
        profile.style = " ".join(layers["style"])
        profile.rules = " ".join(layers["rules"])
        profile.stack = " ".join(layers["stack"])
        profile.interests = " ".join(layers["interests"])
        profile.save()

        self.current_profile = profile
        self.agent = self._make_agent()
        console.print(f"\n[green]✓ Профиль '{name}' создан и активирован.[/]")
        console.print(Panel(profile.to_prompt_text(), title=f"Профиль: {name}"))

    # ── task handlers ─────────────────────────────────────────────────────────

    def _make_coordinator(self, interactive: bool = True) -> TaskCoordinator:
        profile_content = self.current_profile.to_prompt_text() if self.current_profile else ""
        return TaskCoordinator(
            provider=self.provider,
            profile_content=profile_content,
            invariants=self.invariants,
            model=self.model,
            interactive=interactive,
        )

    def _confirm_fn(self, msg: str) -> bool:
        answer = self._prompt(f"{msg} [y/n]: ").strip().lower()
        return answer in ("y", "yes", "д", "да")

    def _handle_task(self, args: list[str]) -> None:
        sub = args[0] if args else "help"

        if sub == "start":
            request = " ".join(args[1:]).strip()
            if not request:
                request = self._prompt("Задача: ").strip()
            if not request:
                return
            task = TaskState.new(request)
            task.profile_name = self.current_profile.name if self.current_profile else ""
            task.model = self.model
            task.save()
            self.current_task = task
            coord = self._make_coordinator(interactive=True)
            self.current_task = coord.run(
                task,
                output_fn=lambda x: console.print(x),
                confirm_fn=self._confirm_fn,
            )

        elif sub == "resume":
            if not self.current_task:
                self.current_task = TaskState.latest()
            if not self.current_task:
                console.print("[red]Нет активной задачи[/]")
                return
            console.print(
                f"[cyan]Resume: {self.current_task.task_id} [{self.current_task.stage.value}][/]"
            )
            coord = self._make_coordinator(interactive=True)
            self.current_task = coord.run(
                self.current_task,
                output_fn=lambda x: console.print(x),
                confirm_fn=self._confirm_fn,
            )

        else:
            console.print("Использование: /task start [запрос] | /task resume")

    # ── invariants handlers ───────────────────────────────────────────────────

    def _handle_invariants(self, args: list[str]) -> None:
        sub = args[0] if args else "list"

        if sub == "list":
            if not self.invariants:
                console.print("[yellow]Инвариантов нет. /invariants add <текст>[/]")
            else:
                for i, inv in enumerate(self.invariants, 1):
                    console.print(f"  {i}. {inv}")

        elif sub == "add":
            text = " ".join(args[1:]).strip()
            if not text:
                text = self._prompt("Инвариант: ").strip()
            if not text:
                return
            add_invariant(text)
            self.invariants.append(text)
            self.agent = self._make_agent()
            console.print(f"[green]✓ Инвариант добавлен[/]")

        else:
            console.print("Использование: /invariants list | /invariants add <текст>")

    # ── chat ──────────────────────────────────────────────────────────────────

    def _stats_line(self, usage: TokenUsage) -> str:
        return (
            f"[dim]↑{usage.prompt_tokens} ↓{usage.completion_tokens} "
            f"= {usage.total_tokens} tok  │  "
            f"{usage.cost_rub:.4f}₽  │  "
            f"{usage.elapsed_ms:.0f}ms[/dim]"
        )

    def _chat(self, user_input: str) -> None:
        chunk_iter, ref = self.agent.respond_stream_with_stats(user_input)

        text = Text()
        with Live(Panel(text, title="[cyan]Assistant[/cyan]", border_style="cyan"), refresh_per_second=15) as live:
            for chunk in chunk_iter:
                text.append(chunk)
                live.update(Panel(text, title="[cyan]Assistant[/cyan]", border_style="cyan"))

        response = text.plain
        usage = ref.usage

        if self.invariants:
            ok, violation = check_llm(response, self.invariants, self.provider, self.model)
            if not ok:
                self.agent.memory.pop_last_exchange()
                self.agent.session_stats.cost_rub -= usage.cost_rub
                self.agent.session_stats.prompt_tokens -= usage.prompt_tokens
                self.agent.session_stats.completion_tokens -= usage.completion_tokens
                self.agent.session_stats.calls -= 1
                console.print(
                    Panel(
                        f"[bold red]Инвариант нарушен:[/bold red] {violation}\n\n"
                        "[dim]Ответ отклонён. Запрос переформулируй без нарушения инвариантов.[/dim]",
                        title="[red]Отказ[/red]",
                        border_style="red",
                    )
                )
                return

        console.print(self._stats_line(usage))

    # ── help ──────────────────────────────────────────────────────────────────

    def _show_help(self) -> None:
        console.print(
            Panel(
                "[bold]Команды:[/bold]\n"
                "  /help                               — эта справка\n"
                "  /model [name]                       — показать / сменить модель\n"
                "  /profile show|list|switch|edit      — управление профилями (День 12)\n"
                "  /profile create [name]              — создать профиль через онбординг\n"
                "  /task start [запрос]                — запустить FSM-пайплайн (День 13)\n"
                "  /task resume                        — продолжить паузу\n"
                "  /state                              — текущее состояние задачи\n"
                "  /invariants list|add [текст]        — инварианты (День 14)\n"
                "  /clear                              — очистить историю диалога\n"
                "  /exit                               — выход\n\n"
                "[dim]Tab — автодополнение команд[/dim]",
                title="Agent CLI — Справка",
            )
        )

    # ── main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        self.invariants = load_invariants()
        self.agent = self._make_agent()

        console.print(
            Panel(
                "[bold cyan]Agent CLI[/bold cyan]  ·  AI Advent Challenge #8\n"
                "[dim]/help — команды  ·  Tab — автодополнение[/dim]",
                border_style="cyan",
            )
        )

        self.session = PromptSession(
            completer=_COMPLETER,
            style=_STYLE,
            bottom_toolbar=self._toolbar,
        )

        while True:
            try:
                user_input = self.session.prompt("▶ ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Выход.[/dim]")
                break

            if not user_input:
                continue

            if not user_input.startswith("/"):
                self._chat(user_input)
                continue

            parts = user_input[1:].split()
            cmd = parts[0].lower() if parts else ""
            args = parts[1:]

            if cmd in ("exit", "quit"):
                console.print("[dim]Выход.[/dim]")
                break
            elif cmd == "help":
                self._show_help()
            elif cmd == "clear":
                self.agent = self._make_agent()
                console.clear()
                console.print("[dim]История очищена.[/dim]")
            elif cmd == "model":
                if args:
                    self.model = args[0]
                    self.agent = self._make_agent()
                    console.print(f"[green]✓ Модель: {self.model}[/]")
                else:
                    console.print(f"Модель: {self.model}")
            elif cmd == "profile":
                self._handle_profile(args)
            elif cmd == "task":
                self._handle_task(args)
            elif cmd == "state":
                if self.current_task:
                    console.print(
                        Panel(
                            f"ID: {self.current_task.task_id}\n"
                            f"Запрос: {self.current_task.request}\n"
                            f"Стадия: {self.current_task.stage.value}\n"
                            f"План: {'есть' if self.current_task.plan else 'нет'}",
                            title="Текущая задача",
                        )
                    )
                else:
                    console.print("[yellow]Нет активной задачи[/]")
            elif cmd == "invariants":
                self._handle_invariants(args)
            else:
                console.print(f"[red]Неизвестная команда: /{cmd}. /help — справка.[/]")
