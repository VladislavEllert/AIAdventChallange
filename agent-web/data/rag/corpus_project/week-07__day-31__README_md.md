<!-- source: week-07/day-31/README.md | title: README.md -->

# Day 31 — фундамент: вторая база знаний + MCP проекта + `/help`

**Видео:** todo

## ⭐ Main Code

| File | What it does |
|------|-------------|
| [`agent-web/agent_web/services/rag/config.py`](../../agent-web/agent_web/services/rag/config.py) | `KNOWLEDGE_BASES = {handbook, project}` registry — index path, label, `rewrite_to_english`, `threshold_answer`, `backend`, `dim` per KB |
| [`agent-web/agent_web/services/rag/embedder.py`](../../agent-web/agent_web/services/rag/embedder.py) | `embed(text, backend=...)` — `ollama` (nomic-embed-text, 768d) or `proxyapi` (text-embedding-3-small, 512d) |
| [`agent-web/agent_web/services/rag/index.py`](../../agent-web/agent_web/services/rag/index.py) | `load_index(path, dim=...)` — fails loudly on vector-length mismatch |
| [`agent-web/agent_web/dependencies.py`](../../agent-web/agent_web/dependencies.py) | `get_rag_index(kb="handbook")` — cache keyed per KB, not a single global |
| [`agent-web/scripts/rag/build_project_corpus.py`](../../agent-web/scripts/rag/build_project_corpus.py) | Builds `data/rag/corpus_project/*.md` from docs + own source + `app.openapi()` dump |
| [`agent-web/scripts/rag/build_index.py`](../../agent-web/scripts/rag/build_index.py) | `--corpus/--out/--backend` flags + `--project` (builds both project indexes in one command) |
| [`agent-web/agent_web/services/commands.py`](../../agent-web/agent_web/services/commands.py) | Slash-command registry — new commands only (`/help` today, `/support`/`/ritual` later) |
| [`agent-web/agent_web/services/commands_help.py`](../../agent-web/agent_web/services/commands_help.py) | `/help` handler — command list, or RAG(`kb=project`) + real git branch via MCP |
| [`mcp-server/project_server.py`](../../mcp-server/project_server.py) | Local FastMCP server (127.0.0.1:8002) — `git_current_branch`, `git_status`, `git_diff`, `list_project_files` |
| [`agent-web/agent_web/services/mcp_client.py`](../../agent-web/agent_web/services/mcp_client.py) | `MCP_SERVERS["project"]` entry + tool labels — transport code untouched |
| [`agent-web/agent_web/routers/chat.py`](../../agent-web/agent_web/routers/chat.py) | New-command dispatch hook + handbook label/threshold now pulled from `KNOWLEDGE_BASES` |
| [`agent-web/frontend/src/components/chat/ChatInput.tsx`](../../agent-web/frontend/src/components/chat/ChatInput.tsx) | `/help <question>` now falls through to the backend instead of being swallowed by the pre-existing client-side static command list |

## Task

Вторая база знаний (RAG по собственному коду и докам проекта) + локальный MCP-сервер, читающий факты о текущей рабочей копии (git-ветка, статус, файлы) + команда `/help`, объединяющая оба: без аргументов — список команд, с вопросом — ответ по проекту с цитатами и текущей git-веткой.

## What was done

**RAG-инфраструктура — multi-KB:**
- `KNOWLEDGE_BASES` в `rag/config.py` — реестр из двух баз (`handbook`, `project`), каждая со своим индексом, лейблом, порогом «не знаю», флагом rewrite и embed-бэкендом.
- `embedder.py` больше не хардкодит `OLLAMA_URL`/`EMBED_MODEL` — `embed(text, backend=...)` поддерживает `ollama` и `proxyapi`.
- `load_index()` проверяет размерность вектора против ожидаемой (`dim` в `KNOWLEDGE_BASES`) и падает с понятной ошибкой при рассинхроне — иначе 768d-запрос по 512d-индексу молча даёт мусорные скоры.
- `get_rag_index(kb=...)` в `dependencies.py` — кеш на несколько баз (`dict[str, list[Chunk]]`), не глобальный синглтон.

**Корпус проекта:**
- `build_project_corpus.py` собирает `data/rag/corpus_project/*.md` из `README.md`, `CLAUDE.md`, `AGENTS.md`, `memory-bank/**` (включая `lessons/`), `week-0*/**/README.md`, исходников `agent-web`/`agent-cli`/`mcp-server`/frontend `src/**`. Исключены `.venv`, `node_modules`, `__pycache__`, `.env`, `data/rag/*.json`.
- Отдельно дампится `app.openapi()` → `corpus_project/api_openapi.md` (paths + схемы) — закрывает пункт задания про API/схемы данных буквально, не только через прозу в README.
- Результат сборки: **147 файлов**, ~73K слов.

**Индексация:**
- `build_index.py` параметризован `--corpus/--out/--backend`; без флагов поведение handbook (два индекса, две стратегии чанкинга, `chunking_compare.md`) не изменилось.
- `--project` строит **оба** индекса проекта одной командой: `index_project.json` (ollama/768d) и `index_project_proxy.json` (proxyapi/512d). На этой машине Ollama (LAN-бокс недели 6) была не поднята — скрипт нелетально пропустил ollama-индекс и построил `index_project_proxy.json` живым вызовом ProxyAPI (194 чанка, 2.9 МБ).
- `KNOWLEDGE_BASES["project"]` по умолчанию указывает на proxyapi-бэкенд (`RAG_PROJECT_BACKEND=ollama` переключает на LAN-индекс, когда тот бокс поднят) — практическое решение: `/help` должно реально работать на машине без доступа к Ollama, а не только «в теории».
- `threshold_answer` для project откалиброван на 10 контрольных вопросах (см. таблицу ниже) — handbook-порог 0.55 калиброван на англоязычном контенте и не подходил.

**Локальный MCP-сервер проекта:**
- `mcp-server/project_server.py` — FastMCP на `127.0.0.1:8002`, читает факты о рабочей копии: `git_current_branch`, `git_status`, `git_diff`, `list_project_files`. Корень репозитория — из env `PROJECT_ROOT`, не из `cwd` (сервер локальный, не на VPS: VPS физически не видит рабочую копию).
- `list_project_files` сандбоксирован через `Path.resolve()` + `is_relative_to(PROJECT_ROOT)` — не обходится симлинками/`../`; `.env`, `.git`, `.venv`, `node_modules`, `*.key` скрыты из листинга.
- `mcp_client.py`: `MCP_SERVERS["project"]` добавлен как третий сервер — код транспорта (`streamable_http_client`) не менялся, он уже был общим для всех серверов. Проверена деградация: сервер выключен → `git_current_branch` отвечает «недоступен», не выдаёт мусор.

**`/help`:**
- Реестр `services/commands.py` — только для новых команд, 4 существующих (`/mcp`, `/history`, `/ping`, `/analyze`) не трогались, дублирование логики не делалось.
- `commands_help.py`: без аргументов — список команд; с вопросом — `kb=project` принудительно (не поле в `ChatRequest` — резолвится на сервере), RAG обязателен, текущая git-ветка инжектится в system-промпт через MCP-тул.
- Rewrite (day 23, перевод запроса на английский) для `project` не вызывается вообще — корпус русскоязычный + код, перевод сбил бы retrieval. Для `handbook` поведение не изменилось.

## Реальный найденный баг

Фронтенд уже содержал **клиентский** обработчик `/help` (`ChatInput.tsx`) — статичный список команд, который **безусловно** перехватывал любое сообщение, начинающееся с `/help`, включая `/help <вопрос>`, и никогда не отправлял его на бэкенд. Backend-реализация была мертва для реального UI, хотя pytest (который бьёт прямо по `/api/chat/stream`, минуя фронтенд) этого не поймал бы. Нашёл живым прогоном в браузере (Playwright), не догадкой. Исправление: `/help` без аргументов остаётся клиентской командой (не менялось), `/help <вопрос>` теперь возвращает `false` из `executeCommand` и падает в обычную отправку на бэкенд.

## Калибровка `threshold_answer` (project KB)

10 контрольных вопросов, реальный proxyapi/512d индекс:

| Вопрос | В базе? | best_score |
|---|---|---|
| как реализован RAG в этом проекте? | да | 0.635 |
| что такое chunk_fixed и chunk_structural? | да | 0.507 |
| какие эндпоинты есть в API agent-web? | да | 0.418 |
| какая модель по умолчанию используется? | да | 0.346 |
| что делает AgentManager? | да | 0.539 |
| как работает rate limit? | да | 0.567 |
| расскажи про день 29 настройки | да | 0.411 |
| на какой я ветке? (не RAG-факт, git) | нет | 0.309 |
| сколько будет 2+2? | нет | 0.264 |
| какой рецепт борща? | нет | 0.225 |

In-KB диапазон 0.35–0.63, out-of-KB диапазон 0.22–0.31 — порог выставлен на **0.33** (зазор между группами).

## Живая проверка

- Реальный uvicorn (`agent-web/.venv/bin/python -m uvicorn agent_web.app:create_app --factory`) + реальный `mcp-server/project_server.py` (`PROJECT_ROOT=<repo root>`).
- `/help как реализован RAG в этом проекте?` → реальные источники (`memory-bank/lessons/week-05-rag.md`, `week-05/day-22/README.md`, ...), реальный стриминг ответа со ссылками на файлы.
- `/help на какой я ветке?` → реальная ветка `main` через MCP (не выдумана моделью).
- Отключение `project_server.py` → `/help` деградирует до «project MCP-сервер недоступен», не выдаёт мусор под видом ветки.
- Playwright: `agent-web/frontend/e2e/help-command.spec.ts` (2 сценария) + регрессия `golden-path.spec.ts` — все 3 зелёные.
- Скриншоты: [`screens/help-rag-question.png`](screens/help-rag-question.png), [`screens/help-git-branch.png`](screens/help-git-branch.png).

## Тесты

```bash
cd agent-web
.venv/bin/python -m pytest tests -q
# 87 passed
```

Новые файлы: `test_rag_corpus.py`, `test_rag_kb.py`, `test_rag_embedder.py`, `test_commands.py`, `test_help_command.py`, `test_rag_rewrite.py`, `test_project_server.py`. Все мокают провайдера/эмбеддер/MCP — ноль живых вызовов ProxyAPI/Ollama в дефолтном прогоне.

## Как запустить локально

```bash
# 1. Собрать корпус проекта + индекс(ы)
cd agent-web
.venv/bin/python scripts/rag/build_project_corpus.py
.venv/bin/python scripts/rag/build_index.py --project   # ollama пропускается, если LAN-бокс не поднят

# 2. Поднять локальный MCP-сервер проекта (отдельный терминал, из корня репо)
PROJECT_ROOT="$(pwd)" agent-web/.venv/bin/python mcp-server/project_server.py

# 3. Поднять agent-web как обычно
cd agent-web && .venv/bin/python __main__.py
```

## Заметки для дня 32

- `RAG_PROJECT_BACKEND` env var переключает project KB между ollama (768d) и proxyapi (512d) индексами — день 32's `RAG_EMBED_BACKEND=proxyapi` в CI (per план) должно мапиться на этот же механизм; свериться перед тем как городить второй.
- Content-hash индекса не записывался (не было в scope дня 31) — день 32.6 просил его для отслеживания протухания baseline при пересборке корпуса днём 33; добавить туда.
- `/mcp` в chat.py показывает «(2 сервера)» текстом, теперь их 3 (finance/github/project) — строка стала неточной. Не трогал по явному указанию плана («не трогать /mcp branch»), но стоит поправить при следующей правке этого блока.
- `chat.py`'s RAG-ветка (day 22-24) делает `return` до цикла tool-calling — как и предупреждал план, это блокер для дня 34, не тронуто в этой фазе.
