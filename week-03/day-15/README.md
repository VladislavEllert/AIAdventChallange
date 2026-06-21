# День 15 — Контролируемые переходы состояний

> ⭐ **Главный код задания:**
> - **[state/machine.py](../../agent-cli/agent_cli/state/machine.py)** — `Stage`, `TRANSITIONS`, `can_transition()` — FSM с явной картой допустимых переходов.
> - **[state/coordinator.py](../../agent-cli/agent_cli/state/coordinator.py)** — `TaskCoordinator.run()` — пайплайн с паузой между стадиями, блокировкой перепрыгивания, pre-pause при resume.
> - **[tui.py](../../agent-cli/agent_cli/tui.py)** — `/task jump <stage>` — команда демо-проверки FSM-перехода.

> ▶ **Видео:** https://drive.google.com/file/d/17tSGsD85Gp4LIqengHKv3sk8l8zB9ZmK/view?usp=share_link

## Цель

Агент с контролируемым жизненным циклом задачи — нельзя перепрыгнуть этап без явного подтверждения пользователя.

## Архитектура

### FSM: явные переходы

```python
TRANSITIONS: dict[Stage, set[Stage]] = {
    Stage.PLANNING:   {Stage.EXECUTION},
    Stage.EXECUTION:  {Stage.VALIDATION},
    Stage.VALIDATION: {Stage.EXECUTION, Stage.DONE},
    Stage.DONE:       set(),
}

def can_transition(from_stage: Stage, to_stage: Stage) -> bool:
    return to_stage in TRANSITIONS.get(from_stage, set())
```

Нельзя:
- `planning → validation` (пропустить execution)
- `planning → done` (пропустить всё)
- `execution → planning` (откат назад)

### Пауза между стадиями

После каждой стадии координатор останавливается и спрашивает:

```
Продолжить → [execution]?
  y/Enter — продолжить  │  n — пауза  │  текст — дать поправки и переработать
```

- `y` → следующая стадия
- `n` → задача сохраняется, выход в обычный чат
- текст → текущая стадия перезапускается с поправками

### Pre-pause при resume

При `/task resume` координатор показывает паузу **перед** запуском стадии — не запускает сразу. Пользователь снова решает: продолжать или нет.

## Демо FSM-блокировки

```
/task start алгоритм Дейкстры
→ план готов → пауза

n                          ← приостановить
→ task.stage = execution

/task jump done            ← попытка перепрыгнуть
→ ❌ ЗАПРЕЩЁН: execution → done
   Допустимые переходы: ['validation']

/task jump planning        ← попытка вернуться назад
→ ❌ ЗАПРЕЩЁН: execution → planning

/task resume               ← вернуться к задаче
→ Продолжить → [execution]?  ← pre-pause (не прыгает сразу)

y → execution → validation → DONE
```

## Команды

```
/task start [запрос]   — запустить задачу (planning → execution → validation)
/task resume           — продолжить после паузы (с pre-pause)
/task jump <stage>     — проверить допустимость FSM-перехода (демо)
/task exit             — выйти из контекста задачи
```
