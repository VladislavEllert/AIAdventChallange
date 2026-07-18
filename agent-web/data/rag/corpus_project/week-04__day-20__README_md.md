<!-- source: week-04/day-20/README.md | title: README.md -->

# День 20 — MCP Orchestration: Multi-Server Pipeline

## 🎯 Цель
Оркестрация нескольких MCP-серверов: VPS (финансы/крипто) + GitHub MCP — LLM строит маршрут сама.

## ⭐ Главный код задания

- **MCP клиент (мульти-сервер)**: [`agent-web/agent_web/services/mcp_client.py`](../../agent-web/agent_web/services/mcp_client.py)
  - `MCP_SERVERS` — реестр серверов: `finance` (VPS 8001) + `github` (VPS 8003)
  - `_tool_registry` — маппинг `tool_name → server_name`, заполняется при старте
  - `_get_all_tools()` — опрашивает все серверы, мержит тулы
  - `_call_tool()` — роутит вызов на нужный сервер по реестру

- **GitHub MCP сервер**: VPS `194.226.115.120:8003` (systemd `mcp-github`)
  - Официальный `@github/github-mcp-server`, Node.js, `--transport streamable-http`
  - Тулы: `create_issue`, `list_issues`, `get_issue`, `search_repositories`, `get_file_contents`

- **Chat router hint**: [`agent-web/agent_web/routers/chat.py`](../../agent-web/agent_web/routers/chat.py)
  - Подсказка LLM: когда использовать `create_issue`, дефолтный `owner/repo`

## 📝 Что реализовано

1. **Два MCP-сервера одновременно**
   - VPS 8001: финансы, крипто (get_crypto_klines, calculate_indicators, web_search, MOEX)
   - VPS 8003: GitHub (create_issue, list_issues, get_file_contents, push_files...)
   - Graceful fallback: если сервер недоступен — остальные работают

2. **Автоматический роутинг тулов**
   - `_tool_registry[tool_name] = server_name` — строится при `get_tools_sync()`
   - `call_tool_sync()` смотрит в реестр → выбирает URL → вызывает
   - LLM не знает про два сервера — видит единый список тулов

3. **Демо-цепочка (4 тула, 2 сервера)**
   - `get_crypto_klines` (VPS 8001) → данные Binance
   - `calculate_indicators` (VPS 8001) → RSI/MACD/сигнал
   - `save_report` (VPS 8001) → файл на VPS
   - `create_issue` (VPS 8003) → GitHub issue с результатами

4. **systemd сервис mcp-github**
   - `npx -y @github/github-mcp-server --transport streamable-http --port 8003`
   - `EnvironmentFile=/opt/mcp-server-code/.env` → `GITHUB_PERSONAL_ACCESS_TOKEN`
   - Рестарт автоматически при падении

## 🧪 Проверка

```bash
# 1. Проверить оба MCP сервера
curl -s http://194.226.115.120:8001/mcp/ | head -c 80
curl -s http://194.226.115.120:8003/mcp/ | head -c 80

# 2. В чате написать:
# "Проанализируй биткоин за последние 50 часовых свечей и создай issue
#  в репозитории AIAdventChallange с заголовком BTC Analysis и результатами"
# → get_crypto_klines → calculate_indicators → save_report → create_issue

# 3. Проверить созданный issue
# https://github.com/VladislavEllert/AIAdventChallange/issues
```

## 📺 Видео
[День 20 — MCP Orchestration Multi-Server](https://drive.google.com/drive/folders/1mPjzjhtExPGUAuEv_Zj0mI6s94kfgVTu?usp=share_link)

## 📚 Знания
- **Multi-server MCP** — единый клиент, реестр маппинга, LLM не знает про топологию
- **Tool registry pattern** — `dict[tool_name → server_url]` строится при инициализации, роутит при вызове
- **GitHub MCP** — официальный Node.js сервер, HTTP transport, токен через env
- **Graceful degradation** — если один сервер упал, агент работает с оставшимися тулами
- **Cross-server pipeline** — LLM сама строит маршрут через тулы разных серверов
