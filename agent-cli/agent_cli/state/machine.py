from enum import Enum

DONE_MARKER = "<<ВЫПОЛНЕНО>>"
PLAN_MARKER = "<<ПЛАН ГОТОВ>>"
VALIDATION_OK_MARKER = "<<ВАЛИДАЦИЯ ОК>>"
VALIDATION_FAIL_MARKER = "<<ТРЕБУЕТ ДОРАБОТКИ>>"


class Stage(str, Enum):
    PLANNING = "planning"
    EXECUTION = "execution"
    VALIDATION = "validation"
    DONE = "done"


TRANSITIONS: dict[Stage, set[Stage]] = {
    Stage.PLANNING: {Stage.EXECUTION},
    Stage.EXECUTION: {Stage.VALIDATION},
    Stage.VALIDATION: {Stage.EXECUTION, Stage.DONE},
    Stage.DONE: set(),
}


def can_transition(from_stage: Stage, to_stage: Stage) -> bool:
    return to_stage in TRANSITIONS.get(from_stage, set())


STAGE_PERSONAS: dict[Stage, str] = {
    Stage.PLANNING: (
        "Ты агент планирования. Твоя задача — создать чёткий структурированный план решения задачи. "
        "Раздели на конкретные шаги. Не решай — только планируй. "
        f"Заверши ответ маркером {PLAN_MARKER}."
    ),
    Stage.EXECUTION: (
        "Ты агент выполнения. Получи план и выполни его шаг за шагом. Будь конкретен. "
        f"Когда всё выполнено, заверши ответ маркером {DONE_MARKER}."
    ),
    Stage.VALIDATION: (
        "Ты агент валидации. Проверь результат выполнения на соответствие плану и инвариантам. "
        f"Если всё ок — заверши ответ маркером {VALIDATION_OK_MARKER}. "
        f"Если есть проблемы — опиши их и заверши маркером {VALIDATION_FAIL_MARKER}."
    ),
    Stage.DONE: "Задача завершена.",
}
