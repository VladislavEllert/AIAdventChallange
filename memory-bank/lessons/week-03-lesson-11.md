# Неделя 3, День 11 — Memory, состояние и stateful-агенты

## Главная идея

Stateless-агент = каждый запрос с нуля. Нет профиля, нет процесса, нет ограничений.
Stateful-агент = управляемая система: знает юзера, этап задачи, инварианты.

## 3 кита stateful-агента

### 1. Профиль (персонализация)

Три группы:
- **style**: кратко/подробно, с примерами/без
- **constraints**: стек, запреты, правила проекта
- **context**: кто юзер, цель, что нужно на выходе

Сбор — стартовое интервью при новом user_id. Хранение: `.md` / DB / API. Скоуп: глобальный / per-project / per-repo / per-file.

Инжекция одинакова везде (Claude / Cursor / Claude Code / ChatGPT) — всё попадает в system prompt:

```
profile = load_profile(user_id)
prompt  = build_prompt(query, profile)
response = llm.generate(prompt)
```

### 2. Task state machine

Стадии: `PLANNING → EXECUTION → VALIDATION → DONE`

Разрешённые переходы (кодом, не промптом):

```kotlin
val transitions = mapOf(
    PLANNING   to listOf(EXECUTION),
    EXECUTION  to listOf(VALIDATION, PLANNING),
    VALIDATION to listOf(DONE, EXECUTION),
    DONE       to emptyList()
)

fun transition(ctx: TaskContext, target: TaskState): TaskContext {
    val allowed = transitions[ctx.state]
    require(target in allowed!!) { "${ctx.state} → $target запрещён" }
    return ctx.copy(state = target)
}
```

**Важно:** текстовые правила теряются после summary/compact. Жёсткие запреты — только кодом.

Сохраняем между сессиями: текущую стадию, утверждённый план, результаты этапов, профиль, constraints.

### 3. Инварианты

Ограничения, не меняющиеся от запроса к запросу: стек, архитектура, запреты библиотек, бюджет, уровень юзера.

Инжектируем в промпт + валидируем ответ кодом:

```kotlin
fun buildPromptWithInvariants(
    query: String, ctx: TaskContext, invariants: List<Invariant>
) = """
    [INVARIANTS]
    ${invariants.joinToString("\n") { it.description }}
    Нарушение любого инварианта ЗАПРЕЩЕНО.
    [STATE] ${ctx.state}  [QUERY] $query
""".trimIndent()
```

Pass → возвращаем ответ + обновляем state. Fail → retry с указанием нарушений.

## Полная архитектура (слайд 31)

```
User Query
    ↓
Profile (style, constraints) + State Machine (этап, шаг, plan) + Invariants (stack, arch, rules)
    ↓
Prompt Builder  →  LLM  →  Validate  →  Pass: Response + State Update
                                    ↘  Fail → retry(violations)
```

Код цикла:

```kotlin
while (true) {
    val query = readQuery()
    val prompt = buildPrompt(query, profile, state, invariants)
    val resp = llm.generate(prompt)
    val result = validate(resp)
    when (result) {
        is Pass -> { send(result.response); state = next(state) }
        is Fail -> retry(result.violations)
    }
}
```

## Антипаттерны

- Класть всё сохранённое в каждый prompt → шум + переполнение
- Полагаться только на текстовые правила без кодовой проверки
- Не валидировать transitions state machine
- Позволять пользователю случайной просьбой ломать стек/процесс

LLM старается помочь → при конфликте промпт vs просьба юзера может нарушить процесс. Важные ограничения — и в prompt, и в коде.

## Вердикт (Влад)

Неделя 3 = достройка агента до production-уровня. Каркас из недели 2 есть (AgentChat, SwiftData, ProxyAPI). Нужно добавить три слоя:
1. **Профиль** — стартовое интервью → сохранение в файл/DB → подмес в system prompt
2. **State machine** — enum стадий + transitions map + персистенция state между сессиями
3. **Инварианты** — список правил → inject в prompt → validate response → retry при нарушении

Всё это уже есть в AgentChat архитектурно (Agent.swift собирает systemPrompt, ProxyAPIClient зовёт LLM). Расширяем существующее, не с нуля.
