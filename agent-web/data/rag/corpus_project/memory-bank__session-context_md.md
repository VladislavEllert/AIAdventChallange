<!-- source: memory-bank/session-context.md | title: session-context.md -->

# Session Context — читать в начале каждой сессии

## ⏩ ACTIVE (2026-07-18) — неделя 7, план готов, следующий шаг `/build`

**Сейчас:** обсуждение и планирование дней 31–35 ЗАВЕРШЕНЫ.
**План: `swarm-report/week07-dev-assistant-plan.md`** — самодостаточный, читать его первым.

Следующая сессия: `/build week07-dev-assistant`, **Sonnet 5 medium**, по фазам
(**E → 0 → 31 → 32 → 33 → 34 → 35**), после каждой фазы `/review`. Открытых блокеров нет.

**Разрешения на неделю 7 (выданы юзером 2026-07-18):**
- ✅ **Push разрешён** — ветки/коммиты/push/PR в `github.com/VladislavEllert/AIAdventChallange`
  без переспрашивания в рамках дней 31–35. Исключение из `CLAUDE.md` §Git на эту неделю.
  Границы: `main` не ломать, force-push нет, секреты не коммитить.
- ✅ Полный доступ к терминалу, агент сам поднимает серверы и тестирует через Playwright.
- ✅ Синтетические тестовые PR дня 32 создавать можно.

**Ключ ProxyAPI:** локально уже в `.env` (gitignored) — ничего вставлять не надо.
В CI — GitHub Secret `PROXYAPI_KEY`, добавляет юзер руками, единственное действие вне агента.
**Значение ключа не писать ни в один файл репо** (`swarm-report/` и планы коммитятся публично).

- Таргет: `agent-web/`. Провайдер: ProxyAPI `openai/gpt-4o-mini`.
- Источники: `week-07/TASK-ORIGINAL.md` (истина по требованиям), `week-07/PLAN-BRIEF.md`.
- Memory: `week07-target-project.md`, `week07-push-allowed.md`.

Ниже — устаревший контекст недели 4 (не трогал, справочно).

---

## Где сейчас

**Текущая неделя:** 4 (MCP)
**Последний сданный день:** 15
**Следующий:** день 16 (тема неизвестна, ждём задания)

Все дни 1–15 сданы. Видео не хватает только дня 15 (нужно снять и вставить).

---

## Платформа (день 12+)

**Всё новое — в `agent-cli/`** (Python, CLI/TUI).
`AgentChat/` (iOS/SwiftUI) — заморожен, не трогаем.

Запуск:
```bash
cd agent-cli
source .venv/bin/activate
python -m agent_cli
```

Модель по умолчанию: `openai/gpt-4o-mini`
API: ProxyAPI (`PROXYAPI_KEY` в `.env`)

---

## Архитектура agent-cli (что реализовано)

### Структура
```
agent-cli/
  agent_cli/
    core/
      agent.py          # Agent: respond/respond_stream_with_stats, memory, persona
      memory.py         # Memory: short_term, summary, add_message, pop_last_exchange
      prompt_builder.py # build_system_prompt(persona, profile, summary, invariants)
      sessions.py       # SessionStore: SQLite, save/load/list/rename/delete
    llm/
      proxyapi.py       # ProxyAPIProvider: chat, stream, models
      provider.py       # TokenUsage, SessionStats, LLMProvider protocol
    profile/
      profile.py        # UserProfile: name/persona/style/rules/stack/interests, save/load
      extractor.py      # route_fact: LLM маршрутизирует факт в нужную секцию профиля
    state/
      machine.py        # Stage enum, TRANSITIONS, can_transition, STAGE_PERSONAS, PLANNING_SWARM
      coordinator.py    # TaskState (JSON-персист), TaskCoordinator.run() — FSM цикл
      swarm.py          # SwarmRunner: run_swarm(×3), synthesize_plan, check_plan, check_execution, final_verdict
    invariants/
      store.py          # load/save/add_invariant → data/invariants/default.yaml
      checker.py        # check_code (regex) + check_llm (LLM-арбитр)
    tui.py              # TUI: REPL, все /команды, toolbar, сессии, профили, задачи
    config.py           # пути: DATA_DIR, TASKS_DIR, SESSIONS_DB, INVARIANTS_DIR
```

### Ключевые потоки

**Чат-запрос:**
```
tui._chat(user_input)
→ agent.respond_stream_with_stats(user_input)
→ _build_messages() → build_system_prompt(persona, profile, summary, invariants) + short_term + input
→ ProxyAPI stream
→ check_llm(response, invariants) — арбитр проверяет
→ если нарушение: pop_last_exchange() + показать отказ
→ _save_current_session()
```

**Task FSM:**
```
/task start "запрос"
→ TaskCoordinator.run(task, output_fn, confirm_fn)
  PLANNING:   SwarmRunner.run_swarm(×3) → synthesize_plan → check_plan
  [пауза]: y=продолжить | n=пауза | текст=фидбек→перезапуск стадии
  EXECUTION:  Agent(EXECUTION).respond(план + фидбек) → check_execution
  [пауза]
  VALIDATION: Agent(VALIDATION).respond(...) → final_verdict
  DONE: _inject_task_into_memory(task) → добавляет в agent.memory как сообщения
```

**Сессии:**
- SQLite: `data/sessions.db` (таблицы: sessions, messages, session_stats)
- При старте: загружает последнюю сессию автоматически
- Сохранение: после каждого ответа + при выходе

### Команды TUI
```
/help                          — все команды
/model <name>                  — сменить модель
/clear                         — очистить историю
/profile new|list|show|switch|edit
/task start|resume|exit|jump <stage>
/session new|list|switch|rename|delete
/invariants list|add <текст>
/state                         — текущая стадия задачи
```

---

## Инварианты (data/invariants/default.yaml)

```yaml
- Строгий запрет мата и нецензурной лексики
- Стек только Python — запрещено предлагать JS/TS/PHP/Ruby
- Запрещено использовать сторонние ORM — только stdlib sqlite3
- Бизнес-правило: запрещено советовать монетизацию без запроса
```

---

## Тесты

```bash
cd agent-cli
source .venv/bin/activate
pytest tests/test_coverage.py -q        # 143 теста, ~91% покрытие
pytest tests/test_coverage.py --cov=agent_cli --cov-report=term-missing
```

---

## Git-состояние

Ветка: `main`. Всё закоммичено. Последние коммиты (дни 13–15):
- `feat(swarm): each agent sees previous colleagues' responses`
- `feat(task): inline feedback during stage pause`
- `fix: Rich markup in confirm msg, orchestrator plan priority`
- `fix: restore session history awareness and profile load order`
- `docs: add day 13/14 video links and READMEs`

---

## Что нужно сделать

- [ ] Снять видео за день 15, вставить ссылку в README и progress.md
- [ ] Ждать задание дня 16 (неделя 4 — MCP)

---

## Идеи к обсуждению

**CLI/TUI vs Web** — переосмыслить platform choice:
- Текущий выбор: CLI/TUI (`agent-cli/`) на Python, из-за MCP/RAG/пайплайнов
- Вариант: веб-интерфейс (сайт) может быть удобнее для реализации фич
- Статус: просто идея, не факт. Смотреть при конкретных задачах недель 4–7
