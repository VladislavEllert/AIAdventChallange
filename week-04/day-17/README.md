# День 17 — MCP Tools: Web Search & MOEX

## 🎯 Цель
Интегрировать инструменты для веб-поиска (Tavily) и получения котировок МосБиржи.

## ⭐ Главный код задания

- **MCP сервер**: [`mcp-server/server.py`](../../mcp-server/server.py) (линии 150-242)
  - `web_search(query, num_results)` — Tavily API
  - `get_moex_quote(ticker)` — текущая цена акции
  - `get_moex_index(ticker)` — текущее значение индекса
  - `get_moex_summary()` — сводка отслеживаемых акций
  - `get_moex_history(ticker, minutes)` — историческая агрегация из SQLite

- **MCP клиент**: [`agent-web/agent_web/services/mcp_client.py`](../../agent-web/agent_web/services/mcp_client.py) — TOOL_LABELS для вывода статуса

- **Chat router**: [`agent-web/agent_web/routers/chat.py`](../../agent-web/agent_web/routers/chat.py)
  - Tool calling loop (строки 219-289)
  - Инъекция текущей даты в system prompt (факт: [СИСТЕМНЫЙ ФАКТ] Текущая дата и время: ...)

## 📝 Что реализовано

1. **Tavily API интеграция** (web_search)
   - API ключ через env: `TAVILY_API_KEY`
   - `include_answer=True` — краткий ответ AI
   - `search_depth="advanced"` — глубокий поиск

2. **MOEX API интеграции**
   - Stock: `https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json`
   - Index: `https://iss.moex.com/iss/engines/stock/markets/index/boards/SNDX/securities/{ticker}.json`
   - Разные эндпоинты для акций и индексов

3. **Автоматическое tool calling**
   - Когда LLM выбирает инструмент, агент вызывает его синхронно
   - Результат добавляется в контекст → LLM решает дальше
   - Loop гарантирует: если нужен веб-поиск, он выполнится перед ответом

4. **Injection текущего времени**
   - Агент ВСЕГДА знает текущую дату (без гаданий)
   - Используется в hint для web_search

## 🧪 Проверка

```bash
# 1. Запустить чат локально
# http://localhost:8000

# 2. Написать: "Какая сейчас цена биткоина?"
# → Автоматически вызовется web_search

# 3. Написать: "Какая цена Сбера?"
# → get_moex_quote(SBER)

# 4. Написать: "Покажи сводку биржи"
# → get_moex_summary()
```

## 📺 Видео
[День 17 — Web Search & MOEX Tools](https://drive.google.com/drive/folders/1mPjzjhtExPGUAuEv_Zj0mI6s94kfgVTu?usp=share_link)

## 📚 Знания
- **LLM tool calling** — модель выбирает какой тул вызвать, агент выполняет
- **Injection vs Hallucination** — дата вводится в prompt, не угадывается моделью
- **MOEX API парсинг** — разные структуры для shares vs index, нужна проверка
