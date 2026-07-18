<!-- source: memory-bank/lessons/week-04-mcp.md | title: week-04-mcp.md -->

# Week 04 — MCP (Model Context Protocol)

Источник: `04_4_неделя_6_поток_v1.md` + конспект `04-mcp-notes.md` + резюме `04-mcp-summary.md`.

## Суть

MCP — открытый стандарт (не framework, не замена API). Единый слой между AI host и внешними сервисами.

```
[User] → [Host + Agent] → [MCP Client] → [MCP Server] → [API / CLI / DB]
                                               ↓
                                          tools/list, tool calls (JSON-RPC 2.0)
```

Transports: **stdio** (локальный subprocess) / **HTTP/SSE** (remote).

## Ключевые роли

- **Host** — приложение с LLM и MCP clients
- **MCP client** — компонент host, держит соединение с одним server
- **MCP server** — процесс/сервис, публикует tools/resources/prompts
- **Tool** — именованная операция: name + description + input schema + handler

## Tool schema влияет на

1. Точность выбора модели
2. Безопасность (validation до выполнения)
3. Размер prompt (token cost)

## Плюсы MCP

- Прямой доступ из AI к внешним системам
- Изолированный доступ (только нужные tools, read-only если надо)
- Единый стандарт — одна интеграция работает с разными AI hosts

## Минусы MCP

- Безопасность: prompt injection, логические бомбы (`rm -rf` через tool)
- Дополнительная инфраструктура (server, TLS, auth)
- Token overhead (подробнее ниже)

## Token flow и стоимость

Токены тратятся при **sampling calls** к LLM. В prompt входят:
- system prompt
- user input
- история
- **все tool schemas** (idle overhead!)
- результаты предыдущих tool calls

Пример из лекции:
- system = ~1500 tok
- user = ~200 tok
- 6 tools × ~900 = ~5400 tok → **даже если tools не нужны**
- tool result = ~3500 tok
- response = ~600 tok

**Три источника overhead:**
1. **Idle overhead** — schemas в контексте всегда, даже если tool не вызван
2. **Batching** — длинная цепочка накапливает историю calls+results
3. **Schema weight** — много детальных tools = тяжёлый prompt

## MCP vs Skill + CLI

| | MCP | Skill + CLI |
|---|---|---|
| Лучше для | Remote, публичные, multi-host | Локальные, CLI уже есть |
| Idle overhead | Есть (schemas всегда) | 0 (загружается on demand) |
| Batching | Хуже (квадратичный рост) | Лучше (можно пачкой) |
| Стандарт | Формальный протокол | Инструкции + bash |

**Вывод Гладкова:** MCP не deprecated полностью. Для удалённых/корпоративных — нужен. Для локального — Skill+CLI часто лучше. Знай оба.

## Цели недели 4

- Подключиться к существующему public MCP server
- Реализовать свой MCP server поверх API
- Оркестрировать несколько tools в агенте
- Сравнить MCP vs Skill+CLI по токенам

## Безопасность (важно)

- Least privilege — минимум tools, read-only по умолчанию
- Строгая validation аргументов, allowlists
- Никакой shell interpolation без sanitization
- Подтверждение destructive actions
- Sandbox, timeouts, audit log
- Не доверять tool results как инструкциям (prompt injection)
