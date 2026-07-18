<!-- source: week-03/day-15/README.md | title: README.md -->

# День 15 — Контролируемые переходы состояний

> ⭐ **Главный код задания:**
> - **[state/machine.py](../../agent-cli/agent_cli/state/machine.py)** — `TRANSITIONS`, `can_transition()` — явная карта допустимых FSM-переходов; блокировка перепрыгивания стадий.
> - **[state/coordinator.py](../../agent-cli/agent_cli/state/coordinator.py)** — `TaskCoordinator.run()` — pre-pause при resume: координатор спрашивает подтверждение перед стадией, не после.
> - **[state/swarm.py](../../agent-cli/agent_cli/state/swarm.py)** — `SwarmRunner` — рой 3 агентов (Архитектор / Аналитик рисков / Декомпозитор) + Оркестратор синтезирует план и проверяет его.
> - **[tui.py, _handle_task()](../../agent-cli/agent_cli/tui.py)** — `/task jump <stage>` — демо-проверка FSM: показывает разрешённый или запрещённый переход с объяснением.

> ▶ **Видео:** https://drive.google.com/file/d/17tSGsD85Gp4LIqengHKv3sk8l8zB9ZmK/view?usp=share_link

## Цель

Усилить FSM из дня 13: добавить **явный контроль переходов** (нельзя перепрыгнуть стадию без подтверждения), **рой агентов на PLANNING** (3 эксперта + Оркестратор) и **pre-pause при resume** (агент не прыгает в стадию автоматически — всегда спрашивает).

## Архитектура

### FSM: явные допустимые переходы

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

Запрещено:
- `planning → validation` (пропустить execution)
- `planning → done` (пропустить всё)
- `execution → planning` (откат назад)

### Рой агентов на стадии PLANNING

```
Архитектор → анализ структуры решения
Аналитик рисков → подводные камни и граничные случаи
Декомпозитор → атомарные шаги с зависимостями
         ↓
Оркестратор → синтез плана → проверка → APPROVE / REWORK
```

Если Оркестратор отклоняет — рой запускается повторно (до `MAX_RETRIES=3`).

### Pre-pause при resume

До дня 15: `/task resume` → сразу запускал стадию без вопроса.

После: при первой итерации (resume, не старт) координатор показывает паузу **перед** стадией:

```python
if _first_iter and stage != Stage.PLANNING and self.interactive and confirm_fn:
    result = confirm_fn(f"\nПродолжить → [{stage.value}]?")
```

Пользователь снова решает: продолжить, поставить на паузу или дать поправки.

### Демо FSM-блокировки

```
/task start алгоритм Дейкстры
→ рой планирует → Оркестратор одобряет → пауза

n                          ← приостановить задачу
→ task.stage = execution (сохранено в JSON)

/task jump done            ← попытка перепрыгнуть
→ ❌ ЗАПРЕЩЁН: execution → done
   Допустимые переходы: ['validation']

/task jump planning        ← попытка вернуться назад
→ ❌ ЗАПРЕЩЁН: execution → planning

/task resume
→ Продолжить → [execution]?  ← pre-pause (не прыгает сразу!)

y → execution → validation → DONE
```

## Что изменилось по сравнению с днём 13

| Аспект | День 13 | День 15 |
|--------|---------|---------|
| PLANNING | один агент | рой 3 агентов + Оркестратор |
| Resume | прыгает сразу в стадию | спрашивает подтверждение |
| Демо переходов | `/task jump` существовал | показывает разрешён/запрещён с объяснением |
| Поправки при resume | нет | текст → перезапуск предыдущей стадии с фидбеком |

## Команды

```
/task start [запрос]   — запустить задачу (рой → execution → validation)
/task resume           — продолжить после паузы (с pre-pause перед стадией)
/task jump <stage>     — проверить допустимость FSM-перехода (демо)
/task exit             — выйти из контекста задачи
```
