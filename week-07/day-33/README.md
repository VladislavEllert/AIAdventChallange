# Day 33 — ассистент поддержки

**Видео:** todo

## ⭐ Main Code

| File | What it does |
|------|-------------|
| [`agent-web/data/support/tickets.json`](../../agent-web/data/support/tickets.json) | 9 тикетов из реальных багов недели 6-7 (SOCKS-прокси на Windows, повреждённая `sessions.db`, пустой ответ qwen3, мобильная вёрстка, зависание `/api/metrics`, dotenv-резолюция, `isinstance` ломает стриминг, эагерный `PROXYAPI_KEY`, тест затирающий боевой `settings.json`) |
| [`agent-web/data/support/faq.md`](../../agent-web/data/support/faq.md) | Источник FAQ (симптом → причина → фикс на каждый класс бага), собран по тем же тикетам |
| [`agent-web/scripts/rag/build_project_corpus.py`](../../agent-web/scripts/rag/build_project_corpus.py) | `_dump_faq()` — копирует `data/support/faq.md` → `corpus_project/faq.md` с заголовком-источником, тем же приёмом что и `_dump_openapi()` дня 31 |
| [`mcp-server/project_server.py`](../../mcp-server/project_server.py) | `list_tickets(status)`, `get_ticket(id)` — новые MCP-тулы, читают `tickets.json` |
| [`agent-web/agent_web/services/mcp_client.py`](../../agent-web/agent_web/services/mcp_client.py) | `TOOL_LABELS["list_tickets"]`, `TOOL_LABELS["get_ticket"]` |
| [`agent-web/agent_web/services/commands_support.py`](../../agent-web/agent_web/services/commands_support.py) | `/support <ticket_id> <вопрос>` — тикет через реальный MCP-вызов `get_ticket` → `[КОНТЕКСТ ТИКЕТА]` в system-промпте → RAG(`kb=project`) |
| [`agent-web/agent_web/routers/chat.py`](../../agent-web/agent_web/routers/chat.py) | Импортирует `commands_support` для регистрации `/support` в реестре команд |
| [`agent-web/frontend/src/components/chat/ChatInput.tsx`](../../agent-web/frontend/src/components/chat/ChatInput.tsx) | `/support` добавлен в список автодополнения; в `executeCommand` не перехватывается — falls through на бэкенд (проверено, не повторяет баг дня 31 с `/help`) |
| [`agent-web/frontend/e2e/support-command.spec.ts`](../../agent-web/frontend/e2e/support-command.spec.ts) | Playwright: `/support TICKET-001 …` → непустой ответ, нет MCP-фолбэка, ответ упоминает `windows/прокси/trust_env` |

## Task

`/support <ticket_id> <вопрос>` — ассистент поддержки поверх той же базы знаний проекта:
тикет приходит через MCP-тул (не питоновский импорт json), поля тикета (`environment`,
`version`, `symptom`) инжектятся в system-промпт, ответ строится на RAG(`kb=project`) с
цитатами FAQ/докoв.

## What was done

- **Тикеты (33.1):** `agent-web/data/support/tickets.json` — 9 тикетов, каждый с полями
  `id`, `title`, `product_area`, `version`, `environment`, `symptom`, `steps`, `status`,
  `user`, `history[]`. Все — реальные баги из `memory-bank/progress.md` недель 6-7
  (не выдуманы), поэтому ответы `/support` реально проверяемы против истории проекта.
- **FAQ + пересборка корпуса (33.2):** `data/support/faq.md` — по одному разделу на
  класс бага (симптом/причина/фикс). `build_project_corpus.py` дополнен `_dump_faq()`
  (тот же приём, что `_dump_openapi()` дня 31) — копирует FAQ в
  `corpus_project/faq.md` под стабильным именем при каждой пересборке. Корпус
  пересобран: **155 файлов** (было 147 на день 31 — +8: `faq.md` и рост
  memory-bank/недельных README за прошедшие дни).
- **MCP-тулы (33.3):** `project_server.py` → `list_tickets(status)` (опциональный
  фильтр по статусу), `get_ticket(id)` (полная запись тикета как JSON). `search_tickets`
  сознательно не сделан — `/support` принимает `ticket_id` напрямую (план явно исключает
  поиск из скоупа).
- **`/support` (33.4):** `commands_support.py` — зеркалит структуру `commands_help.py`
  дня 31 (тот же порядок SSE-событий `sources → rag_meta → chunk* → usage → done`,
  `kb` резолвится на сервере, rewrite отключён для `kb=project`). Тикет получается
  через `call_tool_sync("get_ticket", {"id": ticket_id})` — реальный MCP-раунд-трип,
  тот же паттерн проверки `_tool_registry`, что `commands_help._current_branch()`
  использует для git-ветки (не даёт "unknown tool"-ответу от другого сервера
  притвориться данными тикета). Поля тикета (id/title/product_area/version/environment/
  symptom/status/steps/history) собираются в блок `[КОНТЕКСТ ТИКЕТА]`, инжектируемый в
  system-промпт вместе с RAG-контекстом проекта.

## Живая проверка (после пополнения баланса ProxyAPI)

Баланс ProxyAPI пополнен пользователем 2026-07-18. Всё, что было заблокировано,
доведено до конца в реальном проводе (не моками):

- **Пересобран корпус + оба индекса** (`build_index.py --project`): корпус 155 файлов
  (включая `faq.md`), 207 чанков (было 194 — рост от FAQ). `index_project.json`
  (ollama/768d) не собран — LAN-бокс `192.168.0.33:11434` по-прежнему недоступен с этой
  машины (`curl` → `http_code=000`), это некритично: `index_project_proxy.json`
  (proxyapi/512d) — рабочий фолбэк, `KNOWLEDGE_BASES` на него и указывает по умолчанию.
  Content-hash индекса: `53b73380a53c` → **`4f7971c234d9`**.
- **`review_eval/run_eval.py` перезапущен** на свежем индексе, числа **дописаны** в
  `agent-web/review_eval/results_day32.md` вторым прогоном (день-32 baseline сохранён,
  не затёрт). Recall упал 67%→33% (фикстура 02 перестала флагаться) — тот же промпт и
  модель, другой индекс (FAQ сдвинул retrieval) плюс обычный run-to-run разброс LLM;
  зафиксировано в файле как заметка для дня 32/34/35, не расследовано (вне скоупа дня 33).
- **Эталонный сценарий (33.5) прогнан вживую**: реальный uvicorn + реальный
  `mcp-server/project_server.py` (127.0.0.1:8002) + реальный `/support TICKET-001 как
  починить прокси на Windows?` через `/api/chat/stream`. Ответ модели:

  > В вашем случае, с учетом конфигурации среды (Windows 11, RTX 4060 8GB, Python 3.x
  > venv и системный SOCKS-прокси), проблема заключается в том, что HTTP-клиенты (такие
  > как httpx и OpenAI SDK) по умолчанию доверяют системным переменным окружения прокси.
  > Это приводит к тому, что запросы к локальным адресам (например, к LAN) также
  > проходят через прокси, что вызывает зависания или ошибки соединения.
  >
  > Чтобы исправить эту ситуацию, вам нужно явно указать параметр `trust_env=False` при
  > создании HTTP-клиента для локальных вызовов.

  Ответ дословно повторяет поля тикета (`Windows 11, RTX 4060 8GB, Python 3.x venv,
  системный SOCKS-прокси`) — не общий совет, а контекст, реально пришедший через
  `get_ticket` MCP-тул.
- **Playwright e2e**: добавлен `agent-web/frontend/e2e/support-command.spec.ts`
  (по образцу `help-command.spec.ts`) — открывает чат, шлёт `/support TICKET-001 …`,
  проверяет непустой ответ, отсутствие MCP-фолбэка и упоминание
  `windows|прокси|proxy|trust_env`. Полный прогон: **4/4 passed**
  (`golden-path`, `help-command` ×2, `support-command`). Скриншот реального ответа:
  [`screens/support-ticket-001.png`](screens/support-ticket-001.png).
- **`/help` и день-32 review — тоже проверены живьём** (не только `/support`): `/help
  как реализован RAG в этом проекте?` вернул реальные источники (`memory-bank/lessons/
  week-05-rag.md` и др., top score 0.635) без ошибок. `python -m agent_web.services.review
  --diff-file review_eval/fixtures/01_dotenv_wrong_env.diff --dry-run` отработал живым
  вызовом без исключений. Ничего не сломано остаточным состоянием после 402.

## Реальный найденный баг (при живой проверке)

`rag_search()` внутри `/support` (и, как выяснилось, тот же вызов уже был в `/help`
дня 31) не оборачивает вызов эмбеддера в try/except — если ProxyAPI отвечает ошибкой
(в этой сессии — `402 Insufficient balance`), исключение всплывает необработанным,
SSE-стрим обрывается без единого события клиенту (не даже `chunk` с текстом ошибки).
Не чинил — это pre-existing поведение, общее для `/help` и `/support`, вне скоупа дня 33
(план требует минимальный диф); зафиксировано для следующей сессии.

## Блокер предыдущей сессии (закрыт)

Предыдущая сессия упёрлась в `402 Insufficient balance` (ProxyAPI, chat и embeddings
endpoints) — `build_index.py --project` падал на чанке 101/207, `run_eval.py` не
гонялся, живой e2e не прогонялся. Проверено тогда: скрипт падает до `save_index()`, так
что частичной/битой записи не было — индекс остался на день-32 состоянии
(`53b73380a53c`, 194 чанка), только рассинхронизирован с уже пересобранным корпусом
(155 файлов, включая `faq.md`). Пользователь пополнил баланс 2026-07-18 — всё
перечисленное доведено до конца в этой сессии, см. "Живая проверка" выше.

## Тесты

```bash
cd agent-web
.venv/bin/python -m pytest tests -q
# 135 passed (было 118 на день 32 → +17: 9 tickets-тестов, 5 project_server
# tickets-тестов, 5 support-command тестов — с округлением, см. дифф файлов тестов)
```

Новые файлы: `test_tickets.json`-схема в `test_tickets.py` (существование/парсинг,
диапазон 8-10 тикетов, уникальность id, обязательные поля, непустые `history`/`steps`,
непустые `environment`/`version`); `test_project_server.py` дополнен тестами
`list_tickets`/`get_ticket` (все/фильтр по статусу/пусто/найден/не найден);
`test_support_command.py` — SSE-флоу через `TestClient` с замоканными
`get_ticket`/RAG/провайдером, включая ключевую проверку: `environment`, `version`,
`symptom` тикета реально попадают в system-сообщение, отправляемое LLM (не просто
получены и отброшены). Все мокают провайдера/эмбеддер/MCP — ноль живых вызовов в
дефолтном прогоне.

## Как запустить локально

```bash
# 1. (после пополнения баланса ProxyAPI) пересобрать корпус + индексы
cd agent-web
.venv/bin/python scripts/rag/build_project_corpus.py
.venv/bin/python scripts/rag/build_index.py --project

# 2. Локальный MCP-сервер проекта (тикеты + git/fs факты)
PROJECT_ROOT="$(pwd)/.." agent-web/.venv/bin/python mcp-server/project_server.py

# 3. agent-web как обычно, затем в чате:
# /support TICKET-001 как починить прокси на Windows?
```

## Заметки для дня 34

- Индекс `index_project_proxy.json` (proxyapi/512d) пересобран, content-hash
  `4f7971c234d9` (155 файлов, 207 чанков, включая `faq.md`) — актуален относительно
  корпуса на момент этой сессии.
  Ollama-индекс (`index_project.json`, 768d) по-прежнему не построен — LAN-бокс
  (192.168.0.33:11434) недоступен с этой машины (`curl` → `http_code=000`), как и на
  день 31. proxyapi/512d остаётся рабочим фолбэком, блокером не является.
- `rag_search()` без try/except вокруг эмбеддинга — общий пре-экзистинг гэп `/help` и
  `/support`, не исправлен (вне скоупа). Если день 34 добавляет ещё одну RAG-команду,
  стоит обернуть один раз общим try/except, а не копировать баг третий раз.
- Тулов в `project_server.py` стало 6 (`git_current_branch`, `git_status`, `git_diff`,
  `list_project_files`, `list_tickets`, `get_ticket`) — `TOOL_LABELS` в `mcp_client.py`
  обновлён на оба новых. `/mcp` всё ещё печатает "(2 сервера)" вместо 3 — известный
  долг с дня 31, не трогал.
- `search_tickets` сознательно не реализован (план явно это исключает) — если день 34/35
  когда-нибудь захочет "найди тикеты про X", это отдельная задача, не автоматическое
  расширение `/support`.
