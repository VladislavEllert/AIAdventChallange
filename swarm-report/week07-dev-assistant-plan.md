# Plan: Неделя 7 — растущий ассистент-разработчик над agent-web (дни 31–35)

slug: `week07-dev-assistant`
Дата: 2026-07-18. Собран `/plan` (planner + skeptic). Все правки skeptic HIGH/MED влиты.
Кодит `/build` Sonnet 5 medium по фазам, затем `/review` на каждую фазу.

---

## ⏩ Старт следующей сессии (читать первым)

Этот файл самодостаточен — фаза обсуждения и планирования закрыта. Новая сессия:
`/build week07-dev-assistant`, модель Sonnet 5 medium, по фазам. Порядок фаз:
**E → 0 → 31 → 32 → 33 → 34 → 35**. После каждой фазы — `/review`.

**Разрешения, выданные юзером 2026-07-18 (действуют на всю неделю 7):**

- ✅ **Push разрешён.** Создавать ветки, коммитить, пушить в
  `github.com/VladislavEllert/AIAdventChallange`, открывать PR — можно без переспрашивания
  в рамках задач дней 31–35. Это осознанное исключение из `CLAUDE.md` §Git на эту неделю.
  Границы: `main` не ломать, force-push не делать, `.env`/секреты не коммитить.
- ✅ **Полный доступ к терминалу**, агент сам поднимает серверы и гоняет проверки.
- ✅ Синтетические тестовые PR дня 32 создавать и пушить разрешено (шаг 35.5).

**Ключ ProxyAPI — по ссылке, не по значению:**

- Локально: `PROXYAPI_KEY` уже лежит в `.env` в корне репо (gitignored, проверено).
  Тесты и локальные прогоны читают оттуда. Ничего вставлять не нужно.
- В CI: GitHub Secret с именем `PROXYAPI_KEY`. Добавляет юзер руками через
  Settings → Secrets and variables → Actions. У агента доступа нет.
- **Значение ключа не пишем ни в один файл репо.** `swarm-report/` коммитится в публичный
  репо; ключ в нём = утечка. В workflow — только `${{ secrets.PROXYAPI_KEY }}`.

---

## TL;DR

Один продукт, 5 слоёв поверх `agent-web/`. День 31 — вторая база знаний (RAG по своему коду
и докам) + локальный MCP-сервер проекта + `/help`. День 32 — AI-ревью PR: headless-модуль +
GitHub Action + eval-харнесс на эталонных диффах с метриками. День 33 — `/support` поверх
той же базы + тикеты через MCP. День 34 — tool registry + файловые тулы в песочнице +
human-in-the-loop подтверждение опасных операций. День 35 — chain-агент, который закрывает
наш же ритуал курса (README + progress.md) и коммитит после подтверждения.

Три вещи, найденные при планировании, меняют постановку:

1. **RAG и tool-calling в `chat.py` взаимоисключающи** — RAG-ветка (311) делает `return` на
   453, до цикла тулов (462+). День 34 без правки control flow не работает. Это отдельный
   шаг, не «подмешать схемы».
2. **Эмбеддинги в CI решены.** Проверено живым вызовом: `text-embedding-3-small` на ProxyAPI
   отвечает 200, `dimensions=512` работает. Второй индекс на ProxyAPI-бэкенде, тот же
   `PROXYAPI_KEY`, что уже нужен ревью. BM25 не пишем.
3. **`agent-web/pyproject.toml` не зависит от `agent-cli`**, а `agent_web` импортит
   `agent_cli.*`, и `openai` лежит только в `agent-cli`. `pip install` в Action упадёт на
   импорте.

---

## Acceptance criteria

Проверяет `/review`. «Готово» = pytest зелёный **и** агент лично прокликал в браузере.

**Сквозные (каждая фаза):**
- `pytest agent-web/tests` зелёный, ни одного живого вызова ProxyAPI/Ollama.
- Агент сам прогнал golden path в реальном браузере через Playwright, скриншоты в
  `week-07/day-NN/screens/`.
- Root `README.md` + `memory-bank/progress.md` обновлены (статус done, ссылка на код,
  плейсхолдер `todo` на видео — ссылку вставляет юзер сам, не выдумывать).

**Фаза 0:** дефолтная модель `openai/gpt-4o-mini` в трёх константах **и** в
`agent-web/data/settings.json`; чат в браузере реально отвечает облачной моделью.

**День 31:**
- `/help` отвечает на «как реализован RAG в этом проекте?» с цитатами из
  `agent-web/agent_web/services/rag/*`.
- `/help` на «на какой я ветке?» отдаёт реальный `git rev-parse` через MCP.
- `index_project.json` собран из README/CLAUDE.md/AGENTS.md/`memory-bank/**`/исходников
  **+ `api_openapi.md`** (дамп `app.openapi()` — закрывает буквальный пункт задания
  «схемы данных или API-описания»). Сборка — одна команда.

**День 32:**
- PR в `github.com/VladislavEllert/AIAdventChallange` запускает `.github/workflows/ai-review.yml`,
  бот постит комментарий с тремя секциями: потенциальные баги / архитектурные проблемы /
  рекомендации.
- Та же логика headless: `python -m agent_web.services.review --diff-file <path>`.
- `review_eval` гонит 4 эталонных фикстуры (3 с реальными багами + 1 чистая) и печатает
  recall + latency p50/p95/p99 + cost за прогон + % успешных прогонов.
- `python -m agent_web.services.review score <run_id> <1-5>` пишет human_score в jsonl;
  quality gate считается по последним N оценённым прогонам.

**День 33:**
- `/support <ticket_id> <вопрос>` учитывает поля тикета (environment, version, symptom) и
  цитирует FAQ/доки. Тикет приходит **через MCP-тул**, не питоновским импортом json.

**День 34:**
- Цель уровня «найди все места использования X и обнови по ним доку» → агент САМ вызывает
  `search_files` → `read_file` ×3+ → выдаёт unified diff.
- Опасная операция останавливает поток, в UI модалка с именем тула и аргументами.
  «Отклонить» → файл не изменён (проверено `git status`). **«Разрешить» → файл реально
  изменён на диске** (позитивный кейс обязателен — без него день 35 нечем проверить).
- Повторный прогон на том же состоянии репо даёт тот же список затронутых файлов.

**День 35:**
- `/ritual day <NN>` сам собирает изменения дня, готовит патч к `README.md` и
  `progress.md`, показывает diff, применяет и коммитит только после подтверждения.
  Push не делает никогда.

---

## Plan

### Фаза E — инфраструктура браузерного самотеста (ПЕРВОЙ, до фазы 0)

Идёт первой: фаза 0 требует живой проверки в браузере, а Playwright ставится здесь.

| Шаг | Что |
|---|---|
| E.1 | Добавить `@playwright/test` в devDependencies (сейчас есть только `playwright` — библиотека, раннера нет), `npx playwright install chromium`. |
| E.2 | `agent-web/frontend/playwright.config.ts`: baseURL `http://127.0.0.1:5173`, chromium, trace on-first-retry, **`webServer: [{command, url, reuseExistingServer: true}]`** на uvicorn и vite. Свой bash-скрипт с lsof НЕ пишем — Playwright делает это нативно. |
| E.3 | `agent-web/frontend/e2e/golden-path.spec.ts`: открыть чат, отправить сообщение, дождаться непустого ответа, проверить что инпут снова активен (регрессия «кнопка навсегда зависла»). |
| E.4 | `.claude/skills/e2e-web/SKILL.md`: когда вызывать (перед каждым «готово»), последовательность, что считать провалом, куда класть скриншоты. |
| E.5 | Прогнать на текущем состоянии — обязан проходить ДО дня 31, иначе непонятно что сломала фаза. |

Файлы: `agent-web/frontend/package.json`, `playwright.config.ts`, `e2e/golden-path.spec.ts`,
`.claude/skills/e2e-web/SKILL.md`.

### Фаза 0 — дефолтная модель

| Шаг | Что |
|---|---|
| 0.1 | `agent-cli/agent_cli/config.py:17`, `agent-web/agent_web/services/rag/task_state.py:9` — константы `DEFAULT_MODEL` → `openai/gpt-4o-mini`. |
| 0.2 | `agent-web/agent_web/services/settings_store.py` — ключ `_DEFAULTS["default_model"]` (это ключ словаря, не константа — бриф тут неточен). |
| 0.3 | **`agent-web/data/settings.json` ОТРЕДАКТИРОВАТЬ**, не «проверить». Файл закоммичен, содержит `"default_model": "ollama/qwen3:4b"`, `load_settings` делает `{**_DEFAULTS, **data}` — файл побеждает. Без этой правки код-правка невидима. |
| 0.4 | `pytest agent-web/tests` (conftest импортит `DEFAULT_MODEL` из `agent_cli.config`). `test_models_api` проверяет наличие `ollama/qwen3:4b` в каталоге — не затронуто. |
| 0.5 | Прогон e2e-скилла: чат отвечает облачной моделью. |

### День 31 — фундамент: вторая база знаний + MCP проекта + `/help`

| Шаг | Что |
|---|---|
| 31.1 | `rag/config.py`: `KNOWLEDGE_BASES = {handbook, project}` с полями `index_path`, `label`, `rewrite_to_english`, `threshold_answer`, **`backend`**, **`dim`**. |
| 31.2 | `rag/embedder.py`: `embed(text, backend=...)` с бэкендами `ollama` (nomic-embed-text, 768d) и `proxyapi` (`text-embedding-3-small`, `dimensions=512`). Сейчас `OLLAMA_URL`/`EMBED_MODEL` захардкожены — без этого шага никакой CI-режим не подключается. |
| 31.3 | `scripts/rag/build_project_corpus.py` → `data/rag/corpus_project/*.md` с заголовком `<!-- source: <repo-path> \| title: <name> -->`. Источники: `README.md`, `CLAUDE.md`, `AGENTS.md`, `memory-bank/**/*.md` (включая `lessons/`), `week-0*/**/README.md`, `agent-web/agent_web/**/*.py`, `agent-cli/agent_cli/**/*.py`, `mcp-server/*.py`, `frontend/src/**/*.ts(x)`. Исключить `.venv`, `node_modules`, `__pycache__`, `data/rag/*.json`, `.env`. |
| 31.4 | Туда же: дамп `app.openapi()` → `corpus_project/api_openapi.md` (paths + schemas в markdown). Закрывает пункт задания «схемы данных или API-описания». |
| 31.5 | Параметризовать `scripts/rag/build_index.py` флагами `--corpus/--out/--backend`; без флагов поведение handbook не меняется. Скрипт собирает **оба** индекса проекта одной командой: `index_project.json` (ollama/768) и `index_project_proxy.json` (proxyapi/512). |
| 31.6 | `load_index` проверяет длину вектора против `dim` из `KNOWLEDGE_BASES` и падает громко при рассинхроне. 768d-запрос по 512d-индексу иначе молча скорит мусор. |
| 31.7 | `dependencies.py`: `get_rag_index(kb="handbook")` с кешем `dict[str, list[Chunk]]`. |
| 31.8 | Реестр slash-команд `services/commands.py` — **только для НОВЫХ команд** (`/help`, далее `/support`, `/ritual`). Существующие `/mcp`(138), `/history`(166), `/ping`(179), `/analyze`(238) НЕ трогаем. Ветка image-модели на `chat.py:105` — не slash-команда, не трогать вообще. |
| 31.9 | `chat.py:365` и `chat.py:424`: захардкоженный `"GitLab Handbook"` → `label` из `KNOWLEDGE_BASES`. (Только эти две строки.) |
| 31.10 | `chat.py:367`: `threshold_answer` читать из записи `KNOWLEDGE_BASES`, константу в `rag/config.py` оставить как значение handbook — иначе правка порога регрессит дни 22–24. |
| 31.11 | Отключить query rewrite при `rewrite_to_english=False`. Rewrite переводит запрос на английский под англоязычный handbook; корпус проекта русскоязычный + код, перевод собьёт retrieval. |
| 31.12 | `mcp-server/project_server.py` — локальный FastMCP на `127.0.0.1:8002`: `git_current_branch`, `git_status`, `git_diff`, `list_project_files`. Корень репо из env `PROJECT_ROOT`, не из cwd. Локально, т.к. VPS физически не видит рабочую копию. |
| 31.13 | `mcp_client.py`: `MCP_SERVERS["project"]` + `TOOL_LABELS`. Клиентский код не менять (`streamable_http` универсален). Проверить деградацию при выключенном сервере. |
| 31.14 | `/help` в `commands_help.py`: без аргументов — список команд; с вопросом — `kb=project`, RAG принудительно, инжект текущей ветки через MCP. **`kb` в `ChatRequest`/фронтенд НЕ прокидывать** — резолвится внутри хендлера; поле без UI-переключателя это мёртвая поверхность. |
| 31.15 | Калибровать `threshold_answer` для project на 8–10 контрольных вопросах. 0.55 калиброван на английском handbook и почти наверняка неверен здесь. |
| 31.16 | Тесты + e2e в браузере + `week-07/day-31/README.md` (блок ⭐ в начале) + root README + progress.md. |

Индекс ~4 МБ (замерено: корпус 740K → `index_fixed.json` 3.2M, ×4.3). `index_fixed.json` уже
закоммичен — коммитим и новые, вопрос генерации в CI закрыт.

### День 32 — AI-ревью PR (СОКРАЩЁН, см. Blockers)

| Шаг | Что |
|---|---|
| 32.0 | **Сначала:** добавить `agent-cli` в зависимости `agent-web/pyproject.toml` (или зафиксировать установку обоих пакетов). Проверить в чистом venv: `pip install -e ./agent-cli -e ./agent-web && python -c "import agent_web.services.review"`. Без этого Action падает на импорте (`openai` живёт только в agent-cli). |
| 32.1 | `review/pipeline.py`: `run_review(diff_text, changed_files, kb, model) -> ReviewResult`. Парсинг unified diff → RAG-запросы по именам файлов/символов → промпт → LLM → разбор на три секции. Без обращений к GitHub. |
| 32.2 | `review/resilience.py`: таймаут → retry → fallback-модель → детерминированный отказ («ревью не удалось, нужен человек», exit code ≠ 0, пайплайн не падает). Каждый шаг в метрики. |
| 32.3 | `review/metrics.py` → `data/review_metrics.jsonl` (ts, pr, model, prompt_version, latency_ms, tokens, cost_rub, ok, retries, human_score). Агрегат: p50/p95/p99, cost за прогон, % успешных, quality gate. |
| 32.4 | `review/__main__.py`: `--diff-file \| --pr \| --base/--head`, `--model`, `--dry-run`, `--post-comment`, **`score <run_id> <1-5>`** (иначе quality gate из лекции нечем считать). |
| 32.5 | 4 фикстуры в `review_eval/fixtures/` (.diff + .expected.json) из реальных багов `progress.md`: dotenv frame-based search резолвил не тот .env; `isinstance(provider, ProxyAPIProvider)` ломал стриминг под DispatchProvider; httpx без `trust_env=False` ловил системный SOCKS-прокси; **+1 чистая** (метрика ложных срабатываний). |
| 32.6 | `review_eval/run_eval.py`: recall по ожидаемым находкам + агрегат метрик → `results_day32.md`. Записать content-hash индекса — день 33 пересобирает корпус и иначе baseline протухнет молча. |
| 32.7 | `.github/workflows/ai-review.yml`: `on: [pull_request, workflow_dispatch]`. `checkout` fetch-depth 0 → python 3.12 → `pip install -e ./agent-cli -e ./agent-web` → `git diff origin/$BASE...HEAD` → `python -m agent_web.services.review --post-comment`. `RAG_EMBED_BACKEND=proxyapi`. Ключ только как `${{ secrets.PROXYAPI_KEY }}` — значение в YAML не писать. Права `pull-requests: write`. Условие `if: github.event.pull_request.head.repo.full_name == github.repository` (форки не получают секретов). |
| 32.8 | Smoke через `workflow_dispatch`, не через `act` (Docker на критическом пути не нужен). Ветку «нет ключа» юнит-тестировать прямо в CLI. |
| 32.9 | Тесты + README дня + root README + progress.md. |

Перенесено в день 35 (слак): 3 живых синтетических PR и вторая версия промпта — см. Blockers.

### День 33 — ассистент поддержки

| Шаг | Что |
|---|---|
| 33.1 | `agent-web/data/support/tickets.json` — 8–10 тикетов из **реальных** багов `progress.md` (SOCKS на Windows, повреждённая sessions.db после taskkill /F, пустой ответ qwen3, вёрстка, зависание `/api/metrics`). Поля: id, title, product_area, version, environment, symptom, steps, status, user, history[]. Реальные баги дают проверяемые ответы. |
| 33.2 | `corpus_project/faq.md`, пересобрать **оба** индекса проекта, перезапустить `run_eval.py` и дописать новые числа в `results_day32.md` (не перетирать). |
| 33.3 | В `project_server.py`: `list_tickets(status)`, `get_ticket(id)`. `search_tickets` не нужен — `/support` принимает ticket_id. |
| 33.4 | `commands_support.py`: `/support <ticket_id> <вопрос>` — тикет ЧЕРЕЗ MCP-тул → `[КОНТЕКСТ ТИКЕТА]` в system → RAG `kb=project`. |
| 33.5 | Эталонный сценарий задания на тикете-аналоге; ответ обязан учитывать `environment` из тикета, а не давать общий совет. |
| 33.6 | Тесты + e2e + README + root README + progress.md. |

### День 34 — файловый агент + human-in-the-loop

| Шаг | Что |
|---|---|
| 34.1 | **Control flow в `chat.py` (делать ПЕРВЫМ).** RAG-ветка (311) делает `return` на 453 — цикл тулов (462+) недостижим. Собрать `context_block` в RAG-ветке, инжектить в `all_messages` цикла тулов, убрать ранний `return` когда запрошены тулы. Оставить fast path `use_rag and not tools` для `/help` дня 31, чтобы регрессия была ограничена. |
| 34.2 | `tools/registry.py`: `Tool(name, description, parameters, execute, danger_level)` + `register/get_schemas/get`. |
| 34.3 | `tools/executor.py`: `execute()` → проверка `danger_level` → при DANGEROUS запрос подтверждения → результат. Исключения наружу не пробрасывать. |
| 34.4 | `tools/fs_tools.py`: `read_file`, `search_files` (ripgrep), `list_dir`, `write_file(dry_run=True **по умолчанию, но не единственный режим**)`, `delete_file`. Песочница через `Path.resolve()` + `is_relative_to(REPO_ROOT)` — строковый префикс обходится симлинками и `../`. Запрещены `.env`, `*.key`, `.git/**`, `.venv/**`, `node_modules/**`. |
| 34.5 | `tools/danger.py`: **чистая детерминированная функция** от имени тула + разрешённого пути. LLM-ступень вырезана: LLM в пути авторизации даёт недетерминированное решение + латентность на каждый вызов. Аналогия с `invariants/checker.py` неверна — там проверка контента, а не прав. |
| 34.6 | `tools/confirm.py`: реестр `dict[call_id, {event, approved, payload, session_id}]`. Вместо одного `event.wait(120)` — цикл `while not ev.wait(5): yield ": keepalive\n\n"`, кап 60с. Keepalive-строка инертна для текущего парсера (`chat.ts` реагирует только на `event: `/`data: `). Таймаут — параметр, чтобы тест не спал по-настоящему. Отклонять confirm для сессии, чей стрим уже закончился (протухшая вкладка не должна выполнить запись). |
| 34.7 | `routers/tools.py`: `POST /api/tools/confirm` (**`async def`**), `GET /api/tools`. Зарегистрировать в `agent_web/app.py` (там 10 `include_router`, строки 27–36). |
| 34.8 | SSE `confirm_request`/`confirm_result` в `chat.ts` + `ConfirmToolModal.tsx`: имя тула, аргументы, причина. Кнопки Разрешить/Отклонить, Esc = отклонить. Превью diff — вырезано (gold-plating). |
| 34.9 | Сценарий А: «найди все места использования X и приведи к одному виду» → `search_files` → `read_file` ×N → unified diff. |
| 34.10 | Сценарий Б: «обнови документацию по изменениям в коде» → читает diff и целевой .md → патч → подтверждение на запись. |
| 34.11 | Воспроизводимость: `temperature=0`, сравнивать список затронутых файлов, не побайтовый текст. |
| 34.12 | Живые тесты в браузере — **оба**: негативный (Отклонить → `git status` чист) и позитивный (Разрешить → файл реально изменён). Позитивный обязателен, иначе день 35 непроверяем. |
| 34.13 | Тесты + README дня (указать: требуется один uvicorn worker) + root README + progress.md. |

### День 35 — реальная задача: ритуал курса

| Шаг | Что |
|---|---|
| 35.1 | `rituals/day_report.py` — chain из трёх ролей обычными функциями с разными system-промптами: collector (git diff + файлы дня + метрики) → writer (черновик строки прогресса) → verifier (формат таблицы, наличие ссылок, отсутствие выдумок). Никакого фреймворка субагентов. |
| 35.2 | `tools/git_tools.py`: `git_diff`/`git_log`/`git_status` (безопасные) + `git_commit` (DANGEROUS). `git_push` не пишем вообще — CLAUDE.md запрещает автопуш, тул за флагом это мёртвый код. В README дня записать: push ручной по политике. |
| 35.3 | `commands_ritual.py`: `/ritual day <NN> [--dry-run]` + headless `python -m agent_web.services.rituals.day_report`. |
| 35.4 | Прогон вживую на самом дне 35: собирает изменения, готовит патч, показывает diff, человек подтверждает, агент коммитит. Push не делает. |
| 35.5 | **Слак дня 32:** 3 синтетических PR — (а) утечка ресурса/пустой except, (б) роутер лезет в ФС мимо сервиса, (в) чистый рефакторинг. Ветку создать, запушить, PR открыть — **разрешено, переспрашивать не надо**. Проверить что Action проснулся, поймал баги в (а)/(б) и НЕ выдумал проблем в (в). После проверки ветки закрыть. |
| 35.6 | **Слак дня 32:** вторая версия промпта `PROMPT_V2_STRICT` + сравнение метрик версий. |
| 35.7 | `week-07/day-35/README.md`: формулировка решаемой задачи (прямое требование задания). |
| 35.8 | Финализация: раздел «Неделя 7» в `memory-bank/principles.md`; переписать устаревший `week-07/README.md` (раздел «Открытые вопросы» противоречит PLAN-BRIEF); закрыть дыру exec-routing в `AGENTS.md` (`agent-web/**` и `week-07/**` сейчас «Ask user» — `/build` будет спотыкаться на каждой фазе). |

---

## Тесты

**Правило для всех:** ни один тест не делает живой вызов ProxyAPI/Ollama. Провайдер —
MockProvider из `conftest.py`, эмбеддер — monkeypatch, MCP — monkeypatch на
`call_tool_sync`/`get_tools_sync`. Живые тесты помечаются `@pytest.mark.live` и скипаются
(прецедент: `agent-cli/tests/test_ollama_smoke.py`).

| Область | Тест |
|---|---|
| corpus | Исключения (`.venv`/`node_modules`/`__pycache__`/`.env`) на временном дереве; заголовок парсится существующей `parse_header`. |
| KB | `get_rag_index('project')` и `('handbook')` кешируются раздельно; неизвестный kb → внятная ошибка; индексы подменяются фикстурами. |
| embedder | Бэкенды `ollama`/`proxyapi` выбираются по env; **несовпадение `dim` индекса и бэкенда падает громко**. |
| commands | Новая команда резолвится; неизвестная не перехватывается; 4 legacy-ветки продолжают работать (регрессия). |
| `/help` | TestClient + mock provider + замоканные MCP/эмбеддер. Поток SSE: `sources` → `rag_meta` → `chunk` → `done`. |
| rewrite | `kb=project` → счётчик вызовов rewrite = 0; `kb=handbook` → вызов есть. |
| project_server | `git_current_branch` на временном git-репо; `list_project_files` не выходит за `PROJECT_ROOT`. |
| diff parser | На 4 фикстурах извлекаются файлы и номера строк. Без LLM. |
| resilience | Падающий провайдер → retry → fallback-модель → детерминированный отказ. |
| metrics | Синтетический jsonl из 20 записей → p50/p95/p99, cost, % успешных, quality gate. |
| review CLI | Замоканный провайдер → три секции; ненулевой exit при пустом ответе LLM. |
| tickets | Схема валидна, id уникальны, обязательные поля на месте. |
| `/support` | `get_ticket` замокан; проверить что `environment`/`version` попали в system-сообщение. |
| **песочница** | ТЕСТ БЕЗОПАСНОСТИ, покрыть исчерпывающе: вне `REPO_ROOT`; `../../etc/passwd`; симлинк наружу; `.env` и `*.key` внутри репо. |
| danger | `write`/`delete`/`commit` → DANGEROUS; `read`/`search`/`list` → безопасные. Чистая функция, без LLM. |
| confirm (unit) | Два реальных потока, **без ASGI**: approve → выполняет; deny → диск не тронут (`tmp_path`); таймаут → авто-отказ с малым таймаутом. |
| confirm (SSE) | Только: событие `confirm_request` эмитится, стор предзаполнен, генератор не блокируется. TestClient гоняет ASGI через один блокирующий portal — второй запрос из другого потока во время стрима даёт перемежающиеся зависания. Настоящий end-to-end — в Playwright (34.12). |
| day_report | Collector на временном git-репо; verifier отклоняет черновик со сломанной таблицей или без ссылки. |
| **E2E Playwright** | Перед каждым «готово»: 31 — `/help` с источниками; 33 — `/support` с контекстом тикета; 34 — модалка + отмена **и** подтверждение; 35 — diff ритуала в чате. |

---

## Blockers

**Открытых блокеров нет.** Все четыре сняты — `/build` стартует без вопросов к юзеру.

- ~~Живые PR в публичном репо (35.5)~~ — **разрешено** 2026-07-18, см. блок ⏩ сверху.
  Ветки создаём и пушим, PR открываем. Задание «пайплайн запускается на PR» закрывается
  по-настоящему, а не через `workflow_dispatch`.
- ~~Секрет `PROXYAPI_KEY` в GitHub~~ — юзер добавляет руками (Settings → Secrets → Actions),
  имя `PROXYAPI_KEY`. Единственное действие вне агента. Пока секрета нет, workflow обязан
  деградировать в понятный комментарий, а не в красный CI (шаг 32.8 это тестирует) —
  так что отсутствие секрета не блокирует разработку, только живой прогон на PR.
- ~~Эмбеддинги в CI~~ — проверено живым вызовом, `text-embedding-3-small` отвечает 200,
  `dimensions=512`. Второй индекс на ProxyAPI-бэкенде.
- ~~Размер индекса~~ — ~4 МБ, коммитим, как уже коммичен `index_fixed.json`.

Бюджетное предупреждение остаётся: день 32 даже урезанный самый тяжёлый, день 34 второй
из-за правки control flow в `chat.py`. Если 32 буксует — доделывать параллельно с 33, всю
неделю не сдвигать.

Бюджетное предупреждение: день 32 даже урезанный остаётся самым тяжёлым; день 34 второй по
тяжести из-за правки control flow в `chat.py`. Если 32 буксует — доделывать параллельно с 33,
а не сдвигать всю неделю.

---

## Out of scope

- Реальная CRM для дня 33 — задание явно разрешает JSON.
- Telegram-бот по инвест-сигналам как день 35 — отклонён в PLAN-BRIEF.
- Festrider/GitVerse как целевой проект.
- Новый CLI/TUI — интерфейсом остаётся веб-чат.
- Фреймворк субагентов с параллельным исполнением. Chain в дне 35 обычными функциями;
  fan-out ради fan-out — gold-plating, ни одна наша подзадача не выигрывает от параллелизма.
- UI-дашборд метрик ревью — jsonl + скрипт-агрегатор достаточно.
- Автоматический git push.
- BM25 / гибридный поиск — вопрос снят вторым индексом.
- Миграция 4 работающих команд из `chat.py` в реестр — нулевая польза, горячий файл.
  Вернуться только если день 35 закончится рано.
- `ensure_servers.sh` — `playwright.config.ts webServer` делает это нативно.
- LLM-ступень в `danger.py`, `search_tickets`, `git_push`-тул, превью diff в модалке.
- Переписывание RAG-пайплайна дней 21–25.

---

## Assumptions

- Слэш-диспатч на сервере УЖЕ есть (`chat.py`: `/mcp` 138, `/history` 166, `/ping` 179,
  `/analyze` 238, диапазон 138–309). Утверждение брифа об отсутствии — неточно.
  `chat.py:105` — ветка image-модели, не команда, не трогать.
- `settings_store` правится по ключу `default_model`, не по константе `DEFAULT_MODEL`.
- GitHub MCP-сервер (порт 8003) умеет только issues. Комментарий к PR постится через
  `GITHUB_TOKEN` из Action.
- Целевой репо — `github.com/VladislavEllert/AIAdventChallange` (подтверждено `git remote`).
- Индекс проекта строится fixed chunking (structural на `.py` бессмыслен — нет
  markdown-заголовков).
- Видео записываешь сам; агент ставит плейсхолдер `todo`, ссылку не выдумывает.
- Ollama с nomic-embed-text доступен локально при сборке индексов.
- Локальный MCP через loopback HTTP = корректное «через MCP» (stdio потребовал бы правки
  `mcp_client.py`, который умеет только `streamable_http`).
- Один uvicorn worker (стор подтверждений — модульный dict).
