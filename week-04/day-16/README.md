# День 16 — MCP: Connect & List Tools

## 🎯 Цель
Подключиться к удалённому MCP-серверу на VPS и вывести доступные инструменты.

## ⭐ Главный код задания

- **MCP сервер**: [`mcp-server/server.py`](../../mcp-server/server.py) — FastMCP с 6 инструментами (datetime, web_search, MOEX quote/index/history, get_moex_summary)
- **Клиент**: [`agent-web/agent_web/services/mcp_client.py`](../../agent-web/agent_web/services/mcp_client.py) — подключение к VPS через HTTP
- **Роутер**: [`agent-web/agent_web/routers/chat.py`](../../agent-web/agent_web/routers/chat.py) — `/mcp` команда (строки 83-97)
- **Frontend**: [`agent-web/frontend/src/api/chat.ts`](../../agent-web/frontend/src/api/chat.ts) — SSE стриминг

## 📝 Что реализовано

1. **FastMCP сервер на VPS (194.226.115.120:8001)**
   - 6 инструментов: `get_current_datetime`, `web_search`, `get_moex_quote`, `get_moex_summary`, `get_moex_index`, `get_moex_history`
   - Host: `0.0.0.0` (разрешить внешний доступ)
   - Systemd сервис `mcp-server`

2. **HTTP клиент (мульти-потоочный)**
   - `get_tools_sync()` — получить все инструменты
   - `call_tool_sync(name, args)` — вызвать тул
   - ThreadPoolExecutor + asyncio.run() — избежать "event loop already running"

3. **Команда `/mcp` в чате**
   - Вывести список всех инструментов с описаниями
   - Сгруппировано по функциям (datetime, web, MOEX)

## 🧪 Проверка

```bash
# 1. VPS сервер отвечает
curl -s http://194.226.115.120:8001/mcp/ | head -c 200

# 2. В чате напиши: /mcp
# → Должно вывести список инструментов

# 3. Проверить в браузере
# http://localhost:8000 → чат → /mcp
```

## 📺 Видео
[День 16 — Connect & List Tools](https://drive.google.com/drive/folders/1mPjzjhtExPGUAuEv_Zj0mI6s94kfgVTu?usp=share_link)

## 📚 Знания
- **MCP (Model Context Protocol)** — JSON-RPC 2.0 для LLM tool calling
- **FastMCP** — Python фреймворк (не пиши с нуля, используй декоратор `@mcp.tool()`)
- **DNS rebinding protection** — FastMCP нужен `host="0.0.0.0"`, не `127.0.0.1`
- **Asyncio + FastAPI** — ThreadPoolExecutor для изоляции event loop
