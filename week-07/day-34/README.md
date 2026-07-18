# Day 34 — файловый агент + human-in-the-loop

**Видео:** todo

## ⭐ Main Code

| File | What it does |
|------|-------------|
| [`agent-web/agent_web/services/tools/registry.py`](../../agent-web/agent_web/services/tools/registry.py) | `Tool(name, description, parameters, execute, danger_level)` dataclass + `register()`/`get()`/`get_schemas()` — local (non-MCP) tool registry, schema shape mirrors MCP so chat.py can merge both into one `tool_schemas` list |
| [`agent-web/agent_web/services/tools/danger.py`](../../agent-web/agent_web/services/tools/danger.py) | Pure `danger_level(tool_name, target_path) -> "safe"\|"dangerous"` lookup table — no LLM call, unknown tools fail closed to `dangerous` |
| [`agent-web/agent_web/services/tools/fs_tools.py`](../../agent-web/agent_web/services/tools/fs_tools.py) | `read_file`/`search_files` (ripgrep)/`list_dir` (safe), `write_file`(`dry_run=True` by default, `dry_run=false` for a real write)/`delete_file` (dangerous). Sandbox: `Path.resolve()` + `is_relative_to(REPO_ROOT)`, denylist `.env`/`*.key`/`.git/**`/`.venv/**`/`node_modules/**` |
| [`agent-web/agent_web/services/tools/confirm.py`](../../agent-web/agent_web/services/tools/confirm.py) | Human-in-the-loop registry: `dict[call_id, ConfirmRequest]`, poll loop (`event.wait(poll_interval)` in a bounded `while`) instead of one blocking wait, auto-deny on timeout, auto-deny if the request's SSE "stream session" already ended (stale tab can't approve) |
| [`agent-web/agent_web/services/tools/executor.py`](../../agent-web/agent_web/services/tools/executor.py) | `execute_stream()` — danger check → confirm request/wait (yields SSE-shaped events) → run tool, never lets a tool exception escape raw. `execute()` is a blocking wrapper for headless/unit-test callers |
| [`agent-web/agent_web/routers/tools.py`](../../agent-web/agent_web/routers/tools.py) | `GET /api/tools` (list + schemas), `POST /api/tools/confirm` (`async def`, resolves a pending call) |
| [`agent-web/agent_web/routers/chat.py`](../../agent-web/agent_web/routers/chat.py) | **34.1 control-flow fix**: RAG branch no longer unconditionally `return`s — when tools are also requested, it stashes the RAG excerpts and falls through into the tool-calling loop instead of making it unreachable. Tool loop merges local fs-tool schemas with MCP ones and routes `write_file`/`delete_file` calls through `executor.execute_stream()`, translating `confirm_request`/`keepalive`/`confirm_result` into real SSE frames |
| [`agent-web/frontend/src/api/chat.ts`](../../agent-web/frontend/src/api/chat.ts) | `confirm_request`/`confirm_result` SSE event handling, `confirmTool()` POST helper |
| [`agent-web/frontend/src/components/chat/ConfirmToolModal.tsx`](../../agent-web/frontend/src/components/chat/ConfirmToolModal.tsx) | Modal: tool name, arguments (raw JSON, no diff preview by design), reason. Allow/Deny buttons, Esc = Deny |
| [`agent-web/frontend/src/components/chat/ChatInput.tsx`](../../agent-web/frontend/src/components/chat/ChatInput.tsx) | Wires `pendingConfirm` store state to the modal, `resolveConfirm()` optimistically clears + POSTs the decision |
| [`agent-web/frontend/e2e/tool-confirm.spec.ts`](../../agent-web/frontend/e2e/tool-confirm.spec.ts) | Playwright: scenario A (search_files+read_file → diff, no write), scenario B negative (Deny → disk untouched) and positive (Allow → disk actually changes), all live against a real backend + real ProxyAPI |
| [`agent-web/tests/test_fs_sandbox.py`](../../agent-web/tests/test_fs_sandbox.py) | Security test: escapes REPO_ROOT, `../../etc/passwd`-style traversal, symlink escaping the repo, `.env`/`*.key`/`.git`/`.venv`/`node_modules` blocked even inside the repo |
| [`agent-web/tests/test_danger.py`](../../agent-web/tests/test_danger.py) | Pure-function tests, no LLM |
| [`agent-web/tests/test_confirm.py`](../../agent-web/tests/test_confirm.py), [`test_tools_executor.py`](../../agent-web/tests/test_tools_executor.py) | Real-thread approve/deny/timeout tests (no ASGI); executor tests prove deny leaves `tmp_path` disk untouched and approve actually writes it |
| [`agent-web/tests/test_chat_rag_plus_tools.py`](../../agent-web/tests/test_chat_rag_plus_tools.py) | Regression test for the 34.1 control-flow fix: RAG+tools both on reaches the tool loop (2 LLM calls, not 1); RAG-only fast path stays a single call |

## Task

Файловый агент с песочницей + human-in-the-loop подтверждение опасных операций. Цель:
агент сам вызывает `search_files`/`read_file` для поиска и unification, а любая
операция записи/удаления на диск останавливается модалкой с именем тула и аргументами —
поток продолжается только после явного решения человека (Allow/Deny), с реальным
эффектом на диске, а не только в UI.

## What was done

### 34.1 — control-flow fix в `chat.py` (сделан первым)

RAG-ветка (`if req.use_rag:`) раньше делала `return` сразу после стриминга ответа —
безусловно, даже если тулы тоже были запрошены (`req.use_mcp=True`). Цикл тул-коллинга
ниже по файлу был физически недостижим при включённом RAG. Фикс:

- RAG-ветка теперь ветвится на `if not req.use_mcp:` — старое поведение (стрим + `return`)
  сохранено байт-в-байт для fast-path (чистый RAG-чат, тулы выключены) — регрессии нет.
- Когда `req.use_mcp=True`, RAG-ветка НЕ возвращает: собирает `rag_context_block` +
  `rag_label` + `rag_task_state_block`, оставляет `return` только внутри «don't know»
  gate (там действительно нечего передавать тулам) и внутри except-ветки при
  `not req.use_mcp`. При ошибке RAG и включённых тулах — деградирует мягко (без RAG-контекста
  в тулы), не обрывает ход.
- Ниже, в секции тул-коллинга, `rag_context_block` инжектится в system-сообщение перед
  первым вызовом LLM с тулами (не отдельным сообщением — в тот же hint-блок, где уже
  формируются инструкции по `web_search`/`issue_write`/`search_files`/`write_file`).
- Regression test: [`test_chat_rag_plus_tools.py`](../../agent-web/tests/test_chat_rag_plus_tools.py) —
  `use_rag=True, use_mcp=True` доходит до 2-го (тул-луп) вызова LLM (было физически
  недостижимо); `use_rag=True, use_mcp=False` остаётся single-call fast path.

### 34.2-34.5 — registry + danger + fs_tools

Отдельный пакет `agent_web/services/tools/`, НЕ через MCP (в отличие от дней 31/33) —
чтобы confirm/danger-гейт был вплетён прямо в цикл тул-коллинга `chat.py`, без лишнего
HTTP-прыжка на локальный MCP-сервер. `Tool.schema()` отдаёт тот же JSON-schema формат,
что и MCP-тулы (`{"type":"function","function":{...}}`), поэтому чат просто
конкатенирует `tools_registry.get_schemas()` с `get_tools_sync()`.

Песочница (`fs_tools.resolve_in_sandbox`) — **не** строковый префикс-чек. `Path.resolve()`
разворачивает симлинки и схлопывает `..`, затем `is_relative_to(REPO_ROOT)`. Отдельный
denylist (`.env`, `*.key`, `.git/**`, `.venv/**`, `node_modules/**`) проверяется даже для
путей, которые формально внутри репо — та же логика, что уже была в
`mcp-server/project_server.py` дня 31, продублирована вручную (два разных процесса).

`danger.py` — чистая функция без единого сетевого/LLM-вызова: `dict[str,str]` lookup,
неизвестный тул по умолчанию `dangerous` (fail closed).

### 34.6-34.7 — confirm + router

`confirm.py`: вместо `event.wait(120)` — `while elapsed < timeout: event.wait(poll_interval)`,
на каждый тик (по умолчанию 5с) генератор `wait_for_confirmation()` отдаёт
`("keepalive", None)`, `chat.py` превращает это в `": keepalive\n\n"` — SSE-комментарий,
инертный для парсера `chat.ts` (тот реагирует только на `event: `/`data: `, проверено).
Таймаут — параметр (`confirm_timeout`/`confirm_poll_interval`), тесты не спят настоящие 60с.

Каждый SSE-запрос регистрирует свою собственную "stream session" (`stream_id =
uuid.uuid4().hex`, НЕ `req.session_id` — тот живёт много сообщений) через
`tools_confirm.start_session()`/`end_session()` в `try/finally` вокруг генератора.
Confirm-POST для `call_id`, чья stream session уже закончилась (закрытая/протухшая
вкладка), `resolve()` отклоняет — протухшая вкладка не может задним числом разрешить
запись.

`routers/tools.py`: `GET /api/tools` (список + схемы, для отладки/будущего UI), `POST
/api/tools/confirm` (`async def`) — зарегистрирован в `app.py` в общем стиле остальных
10 роутеров.

### 34.8 — фронтенд

`chat.ts`: два новых SSE-события (`confirm_request`/`confirm_result`), `confirmTool()`
POST-хелпер. `useChatStore`: `pendingConfirm` + `setPendingConfirm`. `ConfirmToolModal.tsx`
— имя тула, аргументы (сырой JSON, без diff-превью — план явно называет это
gold-plating для этой фазы), причина; кнопки Разрешить/Отклонить, Esc = Отклонить.
`ChatInput.tsx` рендерит модалку когда `pendingConfirm` не пуст, `resolveConfirm()`
оптимистично чистит стейт локально и шлёт решение на сервер (сервер тоже пришлёт
`confirm_result`, идемпотентно).

### 34.9-34.12 — живая проверка (МАНДАТОРНАЯ часть фазы)

Все четыре живых сценария прогнаны реальным браузером (Playwright, Chromium) против
реального uvicorn-бэкенда и реального ProxyAPI (`openai/gpt-4o-mini`, temperature из
дефолтных настроек проекта — 0.7, не переопределялся под живые проверки).

**Сценарий A** (34.9) — «найди все места использования X и приведи к одному виду»:
попросил агента найти в `chat.py` все места, где сообщение об ошибке тула форматируется
как `f"Tool error: {e}"` (в файле реально несколько разных стилей — `"Tool error: {e}"`,
`f"Ошибка: {exc}"`, `f"Ошибка расчёта: {e}"` и т.д.), прочитать их и предложить unified
diff к одному виду. Агент САМ вызвал `search_files` → `read_file` несколько раз → выдал
diff в ответе, ничего не записав (`write_file` не вызывался, `git status` подтверждает).
Скриншот: [`screens/day34-scenario-a-diff.png`](screens/day34-scenario-a-diff.png).

**Сценарий B** (34.10) — «обнови документацию по изменениям в коде»: целевой файл —
[`week-07/day-34/TOOLS_DOC_DRAFT.md`](TOOLS_DOC_DRAFT.md), намеренно оставлен со stub-секцией
`TBD — fill in from danger.py`. Агент читает `danger.py` + черновик, пишет реальный список
danger-уровней, вызывает `write_file(..., dry_run=false)` → модалка.

- **Негативный кейс (обязателен):** клик «Отклонить» → `git status` для файла остаётся
  на baseline (файл staged, но не commit-нут — см. "Почему `git add`, не `git commit`"
  ниже), diff пустой. Скриншоты:
  [`screens/day34-scenario-b-modal.png`](screens/day34-scenario-b-modal.png),
  [`screens/day34-scenario-b-deny-clean.png`](screens/day34-scenario-b-deny-clean.png).
- **Позитивный кейс (обязателен — без него день 35 непроверяем):** клик «Разрешить» →
  файл РЕАЛЬНО изменился на диске (`git status` флипает `A` → `AM` — staged+modified),
  проверено `git diff`. Скриншот:
  [`screens/day34-scenario-b-allow-written.png`](screens/day34-scenario-b-allow-written.png).
  Тест восстанавливает файл к baseline после проверки (`git checkout --`), чтобы прогон
  не оставлял LLM-контент как постоянный артефакт в репо.

**Воспроизводимость (34.11):** прогонялся дважды подряд с одним и тем же промптом —
оба раза агент трогал один и тот же файл (`TOOLS_DOC_DRAFT.md`) через один и тот же
маршрут тулов (`read_file` ×2 → `write_file`), т.е. множество затронутых файлов
стабильно. Побайтовый текст ответа/содержимого не сравнивался (temperature=0.7,
дефолт проекта — план 34.11 прямо говорит сравнивать SET затронутых файлов, не текст).

**Честная заметка про флакиность позитивного сценария:** прогонял сценарий B (Allow)
несколько раз подряд, с одним и тем же промптом. Наблюдался заметный разброс: два
прогона отработали чисто (один через реальный браузер за 14.7с — скриншот выше, один
через прямой curl к `/api/chat/stream` за ~3с от клика до записи), два других раза
модель НЕ вызвала `write_file` вовсе за 100-210с ожидания (один раз задала уточняющий
вопрос в тексте вместо вызова тула, другой раз просто не дошла до финального решения в
разумное время) — модалка подтверждения в эти разы даже не появилась, значит баг не в
confirm/executor коде (ему просто нечего было подтверждать). Проверено отдельно прямым
curl-вызовом на `/api/chat/stream` с авто-подтверждением через параллельный poll-скрипт:
при быстром ответе модели механизм confirm→execute→disk отрабатывает корректно и
детерминированно каждый раз (2/2 прямых API-прогонов успешны). Это LLM-вариативность
tool-calling решения (`gpt-4o-mini`, temperature=0.7 — дефолт проекта, не переопределялся),
не баг конфирм-пайплайна: `danger.py`/`confirm.py`/`executor.py` покрыты детерминированными
unit-тестами (`test_confirm.py`, `test_tools_executor.py`) именно чтобы не зависеть от
того, вызовет ли живая модель тул в конкретном прогоне.

### Почему `git add`, не `git commit`, для `TOOLS_DOC_DRAFT.md`

Файл специально застейджен (`git add`, не закоммичен) ДО прогона — иначе его baseline
git-статус — untracked (`??`), который выглядит идентично что до, что после (неважно
что происходило внутри) — тест не мог бы доказать «ничего не изменилось» vs «файл
изменился» через `git status`. Staged-но-не-committed даёт настоящий сигнал: `A ` (не
модифицирован относительно индекса) → `AM` (модифицирован) при реальной записи.
Коммит не делался — это оставлено оркестратору по инструкции недели.

## Тесты

```bash
cd agent-web
.venv/bin/python -m pytest tests -q
# 178 passed (было 135 на день 33 → +43: sandbox/danger/confirm/executor/tools_router/
# rag_plus_tools). Ноль живых вызовов вне explicitly-marked live/Playwright.
```

- **sandbox** (`test_fs_sandbox.py`) — исчерпывающий security-набор: путь вне
  REPO_ROOT, `../../etc/passwd`-трейверсал, символ-линк наружу репо, `.env`/`*.key`/
  `.git`/`.venv`/`node_modules` заблокированы даже внутри репо; write/delete
  dry-run-по-умолчанию и реальная запись отдельно проверены.
- **danger** (`test_danger.py`) — чистая функция, read/search/list = safe,
  write/delete = dangerous, неизвестный тул = dangerous (fail closed), никакого LLM.
- **confirm** (`test_confirm.py`) — два реальных потока: approve разблокирует `True`,
  deny — `False`, таймаут (маленький, не настоящие 60с) — авто-отказ; протухшая
  stream-сессия не может задним числом подтвердить.
- **executor** (`test_tools_executor.py`) — то же самое, но через `execute()`/
  `execute_stream()` с реальным `tmp_path`: deny оставляет диск нетронутым, approve
  реально пишет файл; неизвестный тул и путь-вне-песочницы не пробрасывают исключение
  наружу — только структурированный `{"ok": False, ...}`.
- **tools router** (`test_tools_router.py`) — `GET /api/tools` отдаёт схемы +
  danger_level, `POST /api/tools/confirm` резолвит/отклоняет по `call_id`.
- **34.1 regression** (`test_chat_rag_plus_tools.py`) — доказывает что тул-луп
  ДОСТИЖИМ при `use_rag=True, use_mcp=True` (2 LLM-вызова вместо физически недостижимого
  до фикса), и что fast-path (`use_rag=True, use_mcp=False`) остаётся single-call.
- Полный набор дней 31/32/33 (135 тестов) прогнан вместе — **зелёный**, регрессий нет.

## Playwright e2e (весь набор, включая дни 31/33/34)

```bash
cd agent-web/frontend
npx playwright test
# 7/7 passed: golden-path, help-command×2, support-command, tool-confirm×3
```

## Как запустить локально

```bash
cd agent-web
.venv/bin/python __main__.py     # AGENT_WEB_OPEN_BROWSER=0 для headless
```

В чате — MCP-переключатель включён по умолчанию, локальные fs-тулы (`read_file` и т.д.)
доступны без отдельного тумблера (та же логика `req.use_mcp`, что и MCP-тулы). Спроси
что-то вроде «найди в chat.py все f-строки с 'Ошибка' и приведи к одному виду» или «прочитай
X и обнови Y.md» — при опасной операции появится модалка подтверждения.

## Важно: требуется ОДИН uvicorn worker

`tools/confirm.py` — модульный `dict` в памяти процесса. Второй worker имел бы свой
собственный пустой словарь и никогда не увидел бы подтверждение, отправленное другому
воркеру (тот же паттерн, что и `agent_manager`/`settings_store` — весь `agent-web` уже
однопроцессный по этой причине). Продовый запуск (`uvicorn ... --workers N>1`) сломает
confirm-флоу молча (модалка появится, Allow/Deny уйдёт на другой процесс, стрим
провиснет до auto-deny по таймауту).

## Заметки для дня 35

- Паттерн тула для `day 35`'s `git_tools.py`: имя тула = имя функции в `fs_tools.py`,
  `Tool(name, description, parameters, execute, danger_level)`, регистрация через
  `registry.register()` в модульном `register(...)`-вызове на верхнем уровне файла
  (побочный эффект импорта — тот же приём, что `commands_help`/`commands_support`
  использовали для slash-команд). `git_commit` — DANGEROUS (см. `danger.py`'s
  `test_commit_shaped_name_is_dangerous` — не зарегистрирован пока, но уже
  протестирован как fail-closed через unknown-tool default). `git_push` НЕ должен
  существовать как тул вообще — план прямо это исключает (мёртвый код за флагом).
- `rag_search()` gap (`/help`, `/support` не оборачивают эмбеддер в try/except,
  найдено днём 33) — НЕ тронут. День 34 переписывал control-flow именно в `chat.py`'s
  общем `req.use_rag` пути (не в `commands_help.py`/`commands_support.py`, где живёт
  этот гэп), и тот путь УЖЕ был обёрнут в try/except на уровне chat.py (см. `except
  Exception as e: yield "[RAG error: ...]"` в исходном коде до и после правки 34.1) —
  так что баг остаётся ровно там, где был: в двух slash-командных модулях, не в общем
  RAG-тоггле. Решение: не трогать (вне скоупа дня 34, минимальный дифф).
- Confirm-стор — in-memory, один процесс. Если день 35 когда-нибудь захочет
  multi-worker деплой, это первое, что сломается молча.
