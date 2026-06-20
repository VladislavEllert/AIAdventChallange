# День 13 — Task State Machine: FSM агент с паузой и resume

> ⭐ **Главный код задания:**
> - **[state/machine.py](../../agent-cli/agent_cli/state/machine.py)** — `Stage` enum (planning/execution/validation/done), `TRANSITIONS`, `can_transition()`, персоны агентов по стадиям.
> - **[state/coordinator.py](../../agent-cli/agent_cli/state/coordinator.py)** — `TaskState` (персист в JSON), `TaskCoordinator.run()` — главный цикл FSM: planning→execution→validation→done с паузами между стадиями.
> - **[tui.py, _handle_task()](../../agent-cli/agent_cli/tui.py)** — команды `/task start|resume|exit|jump` — запуск, пауза, возобновление, демо запрещённого перехода.

> ▶ **Видео:** https://www.loom.com/share/e516f7eb3f634c52b6870968d3103ac2

## Цель

Реализовать детерминированный **Task State Machine** — агент не просто отвечает на вопросы, а выполняет задачу через фиксированные стадии с контролем переходов. Доказать: прерывание → resume с сохранённого состояния, запрещённые переходы — явный отказ.

## Архитектура

### FSM (4 стадии)

```
PLANNING → EXECUTION → VALIDATION → DONE
                ↑______________|  (если валидация провалена)
```

- **PLANNING** — агент создаёт структурированный план (`<<ПЛАН ГОТОВ>>`)
- **EXECUTION** — агент выполняет план шаг за шагом (`<<ВЫПОЛНЕНО>>`)
- **VALIDATION** — агент проверяет результат (`<<ВАЛИДАЦИЯ ОК>>` / `<<ТРЕБУЕТ ДОРАБОТКИ>>`)
- **DONE** — задача завершена, результат вносится в память чата

### Детерминированные переходы

```python
TRANSITIONS = {
    Stage.PLANNING:   {Stage.EXECUTION},
    Stage.EXECUTION:  {Stage.VALIDATION},
    Stage.VALIDATION: {Stage.EXECUTION, Stage.DONE},
    Stage.DONE:       set(),
}
```

`/task jump <stage>` → демо: `can_transition()` отказывает при нарушении.

### Пауза и Resume

- Между стадиями: `confirm_fn("Продолжить → [execution]?")` — явное подтверждение
- Ctrl+C в любой момент → `task.save()` → JSON на диске
- `/task resume` → `TaskState.latest()` → продолжает с сохранённой стадии

### Память после задачи

После DONE результат инжектируется в `agent.memory` как реальные сообщения:
```python
memory.add_message("user", f"[Задача: {task.request}]")
memory.add_message("assistant", task.execution_result)
```
Следующие вопросы в чате видят контекст выполненной задачи.

## Команды

```
/task start "запрос"   — запустить новую задачу
/task resume           — продолжить последнюю задачу
/task exit             — выйти из контекста задачи (в обычный чат)
/task jump <stage>     — демо: попытка принудительного перехода
/state                 — показать текущую стадию задачи
```
