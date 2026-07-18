<!-- source: agent-cli/agent_cli/tui.py | title: tui.py -->

from __future__ import annotations

import os
import time
from typing import Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

import agent_cli.config as cfg
from agent_cli.config import DEFAULT_MODEL
from agent_cli.core.memory import MAX_SHORT_TERM
from agent_cli.core.sessions import SessionStore
from agent_cli.llm.provider import TokenUsage
from agent_cli.core.agent import Agent
from agent_cli.invariants.checker import check_llm
from agent_cli.invariants.store import add_invariant, load_invariants
from agent_cli.llm.proxyapi import ProxyAPIProvider
from agent_cli.profile.profile import UserProfile
from agent_cli.state.coordinator import TaskCoordinator, TaskState
from agent_cli.state.machine import Stage, TRANSITIONS, can_transition

console = Console()

_COMMANDS = [
    "/help", "/model", "/clear", "/exit",
    "/profile", "/profile show", "/profile list", "/profile switch", "/profile edit", "/profile create",
    "/task", "/task start", "/task resume", "/task exit", "/task jump",
    "/state",
    "/invariants", "/invariants list", "/invariants add",
    "/session", "/session new", "/session list", "/session switch", "/session rename", "/session delete",
]
_COMPLETER = WordCompleter(_COMMANDS, sentence=True)
_STYLE = Style.from_dict({"bottom-toolbar": "bg:#1e1e1e #666666"})

# Контекстное окно модели gpt-4o-mini в токенах
_CTX_WINDOW_K = 128


class TUI:
    def __init__(self) -> None:
        self.provider = ProxyAPIProvider()
        self.model: str = DEFAULT_MODEL
        self.current_profile: UserProfile | None = None
        self.invariants: list[str] = []
        self.agent: Agent = self._make_agent()
        self.current_task: TaskState | None = None
        self.prompt_session: PromptSession | None = None

        # Менеджер сессий
        self.store = SessionStore(cfg.SESSIONS_DB)
        self.session_id: str = ""

    def _make_agent(self) -> Agent:
        profile_content = self.current_profile.to_prompt_text() if self.current_profile else ""
        return Agent(
            provider=self.provider,
            model=self.model,
            profile_content=profile_content,
            invariants=self.invariants,
        )

    def _session_name(self) -> str:
        meta = self.store.get_meta(self.session_id) if self.session_id else None
        return meta.display_name if meta else "—"

    def _ctx_tok_estimate(self) -> int:
        """Грубая оценка токенов в текущем контексте (символы / 4)."""
        return sum(len(m["content"]) for m in self.agent.memory.short_term) // 4

    def _toolbar(self) -> HTML:
        profile = self.current_profile.name if self.current_profile else "no profile"
        stage = self.current_task.stage.value if self.current_task else "—"
        stats = self.agent.session_stats
        cost_str = f"{stats.cost_rub:.4f}₽" if stats.calls else "0₽"
        ctx_msgs = self.agent.memory.ctx_used
        ctx_tok = self._ctx_tok_estimate()
        ctx_k = f"{ctx_tok / 1000:.1f}K"
        return HTML(
            f"<b>session:</b> {self._session_name()}  "
            f"<b>ctx:</b> {ctx_msgs}msg ~{ctx_k}/{_CTX_WINDOW_K}K  "
            f"<b>model:</b> {self.model}  "
            f"<b>profile:</b> {profile}  "
            f"<b>stage:</b> {stage}  "
            f"<b>₽:</b> {cost_str}"
        )

    def _prompt(self, text: str) -> str:
        """Использует PromptSession если доступен, иначе input()."""
        if self.prompt_session:
            return self.prompt_session.prompt(text)
        return input(text)

    # ── session management ────────────────────────────────────────────────────

    def _save_current_session(self) -> None:
        """Сохраняет текущее состояние агента в БД."""
        if not self.session_id:
            return
        profile_name = self.current_profile.name if self.current_profile else ""
        self.store.save_session(
            self.session_id,
            self.agent.memory,
            self.agent.session_stats,
            model=self.model,
            profile_name=profile_name,
        )

    def _load_session(self, session_id: str) -> None:
        """Загружает сессию в агент."""
        memory, stats, model = self.store.load_session(session_id)
        self.session_id = session_id
        self.model = model
        # Загружаем профиль если был — до создания агента
        meta = self.store.get_meta(session_id)
        if meta and meta.profile_name:
            try:
                self.current_profile = UserProfile.load(meta.profile_name)
            except FileNotFoundError:
                pass
        self.agent = self._make_agent()
        self.agent.memory = memory
        self.agent.session_stats = stats

    def _handle_session(self, args: list[str]) -> None:
        sub = args[0] if args else "list"

        if sub == "list":
            sessions = self.store.list_sessions()
            if not sessions:
                console.print("[yellow]Сессий нет. /session new — создать.[/]")
                return
            table = Table(title="Сессии", show_lines=True)
            table.add_column("Имя", style="cyan")
            table.add_column("ID", style="dim")
            table.add_column("Сообщ.", justify="right")
            table.add_column("~Токены", justify="right")
            table.add_column("₽", justify="right")
            table.add_column("Модель")
            table.add_column("Обновлено")
            for s in sessions:
                active = "▶ " if s.session_id == self.session_id else "  "
                updated = time.strftime("%d.%m %H:%M", time.localtime(s.updated_at))
                # грубая оценка токенов из стоимости (нет точных данных без загрузки)
                table.add_row(
                    active + s.display_name,
                    s.session_id,
                    str(s.msg_count),
                    "—",
                    f"{s.cost_rub:.4f}",
                    s.model,
                    updated,
                )
            console.print(table)

        elif sub == "new":
            # Сохраняем текущую сессию
            self._save_current_session()
            # Авто-имя после 2+ сообщений
            if self.session_id and len(self.agent.memory.short_term) >= 2:
                self.store.auto_name(self.session_id, self.provider, self.model)
            # Создаём новую
            name = " ".join(args[1:]).strip()
            profile_name = self.current_profile.name if self.current_profile else ""
            new_id = self.store.create_session(name=name, model=self.model, profile_name=profile_name)
            self.session_id = new_id
            self.agent = self._make_agent()  # чистый агент
            console.print(f"[green]✓ Новая сессия: {new_id}" + (f" ({name})" if name else "") + "[/]")

        elif sub == "switch":
            target = " ".join(args[1:]).strip()
            if not target:
                console.print("[red]Укажи имя или ID сессии[/]")
                return
            meta = self.store.find_by_name(target)
            if not meta:
                console.print(f"[red]Сессия '{target}' не найдена. /session list[/]")
                return
            self._save_current_session()
            if self.session_id and len(self.agent.memory.short_term) >= 2:
                self.store.auto_name(self.session_id, self.provider, self.model)
            self._load_session(meta.session_id)
            console.print(f"[green]✓ Переключено на: {meta.display_name} ({meta.session_id})[/]")

        elif sub == "rename":
            new_name = " ".join(args[1:]).strip()
            if not new_name:
                new_name = self._prompt("Новое имя: ").strip()
            if not new_name or not self.session_id:
                return
            self.store.rename_session(self.session_id, new_name)
            console.print(f"[green]✓ Сессия переименована: {new_name}[/]")

        elif sub == "delete":
            target = " ".join(args[1:]).strip()
            if not target:
                console.print("[red]Укажи имя или ID сессии[/]")
                return
            meta = self.store.find_by_name(target)
            if not meta:
                console.print(f"[red]Сессия '{target}' не найдена[/]")
                return
            confirm = self._prompt(f"Удалить сессию '{meta.display_name}'? [y/n]: ").strip().lower()
            if confirm not in ("y", "yes", "д", "да"):
                console.print("[dim]Отменено.[/dim]")
                return
            self.store.delete_session(meta.session_id)
            if meta.session_id == self.session_id:
                # Удалили текущую — создаём новую
                self.session_id = self.store.create_session(model=self.model)
                self.agent = self._make_agent()
                console.print("[yellow]Текущая сессия удалена, создана новая.[/]")
            else:
                console.print(f"[green]✓ Сессия удалена: {meta.display_name}[/]")

        else:
            console.print("Использование: /session new|list|switch|rename|delete")

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
            chat_summary=self.agent.memory.summary,
        )

    def _confirm_fn(self, msg: str) -> str | None:
        """
        Возвращает:
          ""   — продолжить (y/enter)
          None — приостановить (n)
          str  — фидбек пользователя → перезапустить стадию с поправками
        """
        from rich.markup import escape
        console.print(f"[dim]{escape(msg)}[/dim]")
        console.print("[dim]  y/Enter — продолжить  │  n — пауза  │  текст — дать поправки и переработать[/dim]")
        try:
            answer = self._prompt("▶ ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if not answer or answer.lower() in ("y", "yes", "д", "да"):
            return ""
        if answer.lower() in ("n", "no", "н", "нет"):
            return None
        return answer  # фидбек → перезапуск стадии

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
            self._inject_task_into_memory(self.current_task)

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
            self._inject_task_into_memory(self.current_task)

        elif sub == "jump":
            # Демо: попытка принудительно перепрыгнуть стадию
            if not self.current_task:
                console.print("[yellow]Нет активной задачи. /task start [запрос][/]")
                return
            target_str = args[1] if len(args) > 1 else ""
            if not target_str:
                console.print("[red]Укажи стадию: planning | execution | validation | done[/]")
                return
            try:
                target = Stage(target_str.lower())
            except ValueError:
                console.print(f"[red]Неизвестная стадия: '{target_str}'. "
                              f"Доступны: planning, execution, validation, done[/]")
                return
            current = self.current_task.stage
            if can_transition(current, target):
                console.print(
                    Panel(
                        f"[green]Переход разрешён:[/green] {current.value} → {target.value}\n"
                        "[dim](FSM-переход допустим, но выполняется через /task resume)[/dim]",
                        title="FSM: переход",
                        border_style="green",
                    )
                )
            else:
                allowed = [s.value for s in TRANSITIONS.get(current, set())]
                console.print(
                    Panel(
                        f"[bold red]Переход ЗАПРЕЩЁН:[/bold red] "
                        f"{current.value} → {target.value}\n\n"
                        f"Текущая стадия: [yellow]{current.value}[/yellow]\n"
                        f"Допустимые переходы: [green]{allowed or 'нет (задача завершена)'}[/green]\n\n"
                        "[dim]FSM не позволяет перепрыгивать этапы.\n"
                        "Нельзя делать реализацию до утверждённого плана,\n"
                        "нельзя финализировать без валидации.[/dim]",
                        title="[red]FSM: недопустимый переход[/red]",
                        border_style="red",
                    )
                )

        elif sub == "exit":
            if not self.current_task:
                console.print("[yellow]Нет активной задачи.[/]")
            else:
                self.current_task = None
                console.print("[dim]Вышел из контекста задачи. Обычный чат.[/dim]")

        else:
            console.print("Использование: /task start [запрос] | /task resume | /task exit | /task jump <stage>")

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
            console.print("[green]✓ Инвариант добавлен[/]")

        else:
            console.print("Использование: /invariants list | /invariants add <текст>")

    # ── task memory integration ───────────────────────────────────────────────

    def _inject_task_into_memory(self, task: "TaskState | None") -> None:
        """После завершения задачи вносим результат в память чата как реальные сообщения."""
        if not task or task.stage != Stage.DONE:
            return
        if not task.execution_result:
            return
        self.agent.memory.add_message("user", f"[Задача: {task.request}]")
        self.agent.memory.add_message("assistant", task.execution_result)

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
        # Автосохранение сессии после каждого ответа
        self._save_current_session()

    # ── help ──────────────────────────────────────────────────────────────────

    def _show_help(self) -> None:
        console.print(
            Panel(
                "[bold]Команды:[/bold]\n"
                "  /help                                  — эта справка\n"
                "  /model [name]                          — показать / сменить модель\n"
                "\n[bold]Сессии (День 15):[/bold]\n"
                "  /session new [name]                    — новая сессия\n"
                "  /session list                          — список всех сессий\n"
                "  /session switch <name|id>              — переключить сессию\n"
                "  /session rename <name>                 — переименовать текущую\n"
                "  /session delete <name|id>              — удалить сессию\n"
                "\n[bold]Профили (День 12):[/bold]\n"
                "  /profile show|list|switch|edit         — управление профилями\n"
                "  /profile create [name]                 — создать профиль\n"
                "\n[bold]Задачи — FSM (Дни 13–15):[/bold]\n"
                "  /task start [запрос]                   — запустить пайплайн (рой агентов)\n"
                "  /task resume                           — продолжить после паузы\n"
                "  /task exit                             — выйти из контекста задачи\n"
                "  /task jump <stage>                     — проверка FSM-перехода (демо)\n"
                "  /state                                 — текущее состояние задачи\n"
                "\n[bold]Инварианты (День 14):[/bold]\n"
                "  /invariants list|add [текст]           — управление инвариантами\n"
                "\n"
                "  /clear                                 — очистить историю диалога\n"
                "  /exit                                  — выход\n\n"
                "[dim]Tab — автодополнение  ·  Toolbar — сессия / ctx / модель / ₽[/dim]",
                title="Agent CLI — Справка",
            )
        )

    # ── main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        self.invariants = load_invariants()

        # Инициализация / восстановление сессии
        last_id = self.store.last_session_id()
        if last_id:
            try:
                self._load_session(last_id)
                console.print(f"[dim]Восстановлена сессия: {self._session_name()} ({last_id})[/dim]")
            except Exception:
                self.session_id = self.store.create_session(model=self.model)
        else:
            self.session_id = self.store.create_session(model=self.model)

        self.agent = self._make_agent() if not self.session_id else self.agent

        console.print(
            Panel(
                "[bold cyan]Agent CLI[/bold cyan]  ·  AI Advent Challenge #8\n"
                "[dim]/help — команды  ·  Tab — автодополнение  ·  "
                "/session list — сессии[/dim]",
                border_style="cyan",
            )
        )

        self.prompt_session = PromptSession(
            completer=_COMPLETER,
            style=_STYLE,
            bottom_toolbar=self._toolbar,
        )

        while True:
            try:
                user_input = self.prompt_session.prompt("▶ ").strip()
            except (EOFError, KeyboardInterrupt):
                self._save_current_session()
                console.print("\n[dim]Выход. Сессия сохранена.[/dim]")
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
                self._save_current_session()
                console.print("[dim]Выход. Сессия сохранена.[/dim]")
                break
            elif cmd == "help":
                self._show_help()
            elif cmd == "clear":
                self.agent = self._make_agent()
                # Пересоздаём сессию (старая очищена)
                self.session_id = self.store.create_session(
                    model=self.model,
                    profile_name=self.current_profile.name if self.current_profile else "",
                )
                console.clear()
                console.print("[dim]История очищена. Новая сессия создана.[/dim]")
            elif cmd == "model":
                if args:
                    self.model = args[0]
                    self.agent = self._make_agent()
                    console.print(f"[green]✓ Модель: {self.model}[/]")
                else:
                    console.print(f"Модель: {self.model}")
            elif cmd == "session":
                self._handle_session(args)
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
