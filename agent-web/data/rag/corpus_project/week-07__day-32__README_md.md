<!-- source: week-07/day-32/README.md | title: README.md -->

# Day 32 — AI-ревью PR (сокращён, см. Blockers плана)

**Видео:** todo

## ⭐ Main Code

| File | What it does |
|------|-------------|
| [`agent-web/agent_web/services/review/pipeline.py`](../../agent-web/agent_web/services/review/pipeline.py) | `run_review()` — diff-in, `ReviewResult`-out. Unified-diff parser (files + line numbers), RAG-запросы по имени файла/символа, промпт, парсинг ответа на 3 секции. Без GitHub API. |
| [`agent-web/agent_web/services/review/resilience.py`](../../agent-web/agent_web/services/review/resilience.py) | `call_with_resilience()` — таймаут → retry primary → fallback-модель → детерминированный отказ (`"review failed, needs human"`). Никогда не бросает исключение наружу. |
| [`agent-web/agent_web/services/review/metrics.py`](../../agent-web/agent_web/services/review/metrics.py) | `data/review_metrics.jsonl` — запись/чтение прогонов, `aggregate()` → p50/p95/p99, cost/прогон, % успешных, quality gate по последним N оценённым. |
| [`agent-web/agent_web/services/review/__main__.py`](../../agent-web/agent_web/services/review/__main__.py) | CLI: `--diff-file \| --base/--head`, `--model`, `--dry-run`, `--post-comment`, подкоманда `score <run_id> <1-5>`. |
| [`agent-web/review_eval/fixtures/`](../../agent-web/review_eval/fixtures/) | 4 эталонные фикстуры (3 реальных бага из `progress.md` + 1 чистая) — `.diff` + `.expected.json`. |
| [`agent-web/review_eval/run_eval.py`](../../agent-web/review_eval/run_eval.py) | Живой eval-харнесс (НЕ pytest) — реальные вызовы ProxyAPI, recall/FP-rate/latency/cost → `results_day32.md`. |
| [`agent-web/review_eval/results_day32.md`](../../agent-web/review_eval/results_day32.md) | Реальные числа последнего живого прогона (см. ниже). |
| [`.github/workflows/ai-review.yml`](../../.github/workflows/ai-review.yml) | `on: [pull_request, workflow_dispatch]` → устанавливает оба пакета → строит диф → `python -m agent_web.services.review --post-comment`. |
| [`agent-web/pyproject.toml`](../../agent-web/pyproject.toml) | Комментарий, документирующий обязательную совместную установку `agent-cli` + `agent-web` (см. «Что не получилось сделать красиво» ниже). |

## Task

Из плана (`swarm-report/week07-dev-assistant-plan.md`, «День 32 — AI-ревью PR (СОКРАЩЁН, см. Blockers)»): AI-ревью PR headless-модулем + GitHub Action + eval-харнесс на эталонных диффах с метриками. Урезано против исходного брифа — 3 живых синтетических PR и вторая версия промпта перенесены в день 35 (см. план, «Перенесено в день 35»).

## What was done

**32.0 — совместная установка пакетов.** `agent_web` импортирует `agent_cli.*` (провайдеры, `DEFAULT_MODEL`), а `openai` живёт только в зависимостях `agent-cli`. Проверено в чистом venv: `pip install -e ./agent-web` без `agent-cli` → `ModuleNotFoundError: agent_web` уже на самом первом шаге (пакет даже не установился, т.к. build backend не находит зависимость на PyPI... на деле просто ничего не установилось, import падает). После `pip install -e ./agent-cli -e ./agent-web` → `import agent_web.services.review` работает. Пытался объявить `agent-cli` как relative `file://` зависимость в `pyproject.toml` — pip 25 отклоняет нелокальные/переменные `file://` URI («non-local file URIs are not supported»), реальной поддержки относительных путей в dependency-спецификаторе нет. Решение: не хак, а гарантия на уровне процесса — везде, где ставится `agent-web`, ставится и `agent-cli` (CI workflow, дев-окружение), плюс явный комментарий в `pyproject.toml`.

**32.1 — pipeline.** `parse_diff()` — чистый парсер unified diff (без LLM): извлекает путь файла и номер строки в новом файле для каждой добавленной строки, ходит по хидерам `diff --git`/`@@ ... @@`. `build_rag_queries()` — запросы по пути файла + `<путь> <символ>` для каждого `def`/`class`, добавленного в диффе (капается на 5 запросов — cost/latency). `run_review()` принимает `chat_fn` инъекцией — сам не знает про провайдера, только про (messages, model) → text; это то, что делает модуль тестируемым без сети и держит retry/fallback снаружи, в resilience.py.

**32.2 — resilience.** Лесенка: primary-модель (с `max_retries` повторами, каждая попытка через `ThreadPoolExecutor` с таймаутом) → fallback-модель (один раз, если задана и отличается) → `ok=False` с `DETERMINISTIC_FAILURE_MSG`. Любое исключение (сетевое, авторизация, таймаут, «пустой ответ LLM» — пайплайн сам бросает `RuntimeError` при `result.ok=False`) считается неудачной попыткой. Каждая попытка отдаётся в `on_attempt` — CLI пишет это в метрики.

**32.3 — metrics.** `data/review_metrics.jsonl`, одна строка на прогон. `aggregate()` — p50/p95/p99 (линейная интерполяция), средний cost, % успешных, quality gate = среднее `human_score` по последним N *оценённым* прогонам (не по всем — неоценённые не в счёт). Нашёл и поправил баг в собственном коде до коммита: `path: Path = METRICS_PATH` как default-параметр биндится один раз при импорте модуля — monkeypatch `metrics.METRICS_PATH` в тестах молча игнорировался, и тестовые записи реально утекали в `data/review_metrics.jsonl` в репозитории. Поймано ре-запуском тестов и сверкой содержимого файла на диске, не догадкой. Исправлено на `path: Path | None = None` + резолюция внутри тела функции; утёкшие тестовые записи вычищены из `data/review_metrics.jsonl` вручную.

**32.4 — CLI.** `argparse` с сабкомандой `score`; без сабкоманды — режим ревью (`--diff-file` или `--base`/`--head` + `git diff`). `--dry-run` — прогоняет и печатает, но не пишет метрики и не постит комментарий (для локальных проверок). `--post-comment` постит через `httpx` на GitHub REST API, авторизация — `GITHUB_TOKEN`/`GITHUB_REPOSITORY` из окружения Action, номер PR — из `--pr` или `$GITHUB_EVENT_PATH`; при отсутствии токена/репо/номера — предупреждение в stderr, не падение.

**32.5 — фикстуры.** 4 штуки в `review_eval/fixtures/`, из реальных багов недели 6 (`memory-bank/progress.md`, дни 27 и Windows-деплой):
1. `01_dotenv_wrong_env` — `load_dotenv()` без `find_dotenv(usecwd=True)`, frame-based резолюция берёт не тот `.env`.
2. `02_isinstance_breaks_streaming` — `isinstance(provider, ProxyAPIProvider)` ломается, когда `self.provider` — обёртка `DispatchProvider`.
3. `03_httpx_missing_trust_env` — `httpx.Client` без `trust_env=False` ловит системный SOCKS-прокси.
4. `04_clean_refactor` — чистый рефакторинг (вынос `_dot` в именованный `_cosine_score` с докстрингом), баг не заложен — измеряет false positive rate.

Диффы — представительные (та же природа бага), не байт-в-байт исторические — реальных исходных диффов недели 6 в git-истории в чистом виде для точечного воспроизведения нет, инструкция плана это разрешает.

**32.6 — eval-харнесс.** `review_eval/run_eval.py` — **живой** инструмент (реальные вызовы ProxyAPI), НЕ pytest — специально прописано почему в докстринге модуля: recall без реальной модели ничего не значит, а мок ради pytest-совместимости был бы фальшивой метрикой. Пишет `results_day32.md` с recall / false positive rate / latency p50-p95-p99 / cost / % успешных + **content-hash индекса** (`sha256[:12]` от `index_project_proxy.json`) — день 33 пересобирает корпус проекта, и без хэша непонятно, устарел ли baseline.

**32.7 — workflow.** `.github/workflows/ai-review.yml`: `on: [pull_request, workflow_dispatch]`, `checkout` с `fetch-depth: 0`, python 3.12, `pip install -e ./agent-cli -e ./agent-web`, `git diff origin/<base>...HEAD`, `python -m agent_web.services.review --post-comment`. `RAG_EMBED_BACKEND=proxyapi` (LAN-Ollama недоступен раннеру). Ключ только как `${{ secrets.PROXYAPI_KEY }}`. Права `pull-requests: write`. Guard на форки (`head.repo.full_name == github.repository`) — форки не получают секретов. Отдельный шаг ставит понятный комментарий вместо красного CI, если `PROXYAPI_KEY` не сконфигурирован (Blockers плана это явно требует).

**32.8 — деградация без ключа.** Юнит-тест (`test_cmd_review_degrades_on_provider_failure_no_api_key`) симулирует падение `provider.chat_with_stats` на каждом вызове — CLI отрабатывает лесенку (primary×2 + fallback×1 = 3 попытки), возвращает `DETERMINISTIC_FAILURE_MSG` в stderr и код возврата 1, не падает. Живой smoke через `workflow_dispatch` **отложен** — нужен реальный push юзера с добавленным GitHub Secret `PROXYAPI_KEY`, вне возможностей агента в этой фазе.

## Проверено реально (не только pytest)

**`pytest agent-web/tests`:**
```
118 passed, 57 warnings in 51.75s
```
Зелёный целиком, включая все тесты предыдущих фаз (E, 0, день 31). Ноль живых вызовов кроме явно помеченных — новых тестов дня 32 не помечал `@pytest.mark.live`, т.к. все они целиком на стабах/моках (`_StubProvider`, синтетический jsonl, чистые функции парсера).

**Живой прогон CLI** (`python -m agent_web.services.review --diff-file review_eval/fixtures/02_isinstance_breaks_streaming.diff --dry-run`, реальный вызов ProxyAPI, `openai/gpt-4o-mini`):
```
### AI Review (run `ae00e31e`, model `openai/gpt-4o-mini`)

## Potential bugs
- none found

## Architectural issues
- none found

## Recommendations
- Consider adding logging or error handling around the conditional logic in
  `respond_stream_with_stats` (line 89) to capture potential issues when the
  provider is not `ProxyAPIProvider`. This could help in debugging if
  unexpected behavior occurs with other providers.
```
Модель не назвала это багом напрямую (упомянула условную ветку в рекомендациях, не в bugs) — честный результат живого прогона, не подогнан.

**Живой прогон eval-харнесса** (`python review_eval/run_eval.py`, 4 реальных вызова ProxyAPI):

| fixture | bug_class | expect_flag | flagged | ok | latency_ms |
|---|---|---|---|---|---|
| 01_dotenv_wrong_env | dotenv-wrong-env-resolution | True | **True** | True | 3580 |
| 02_isinstance_breaks_streaming | isinstance-breaks-dispatch-wrapper | True | **True** | True | 2806 |
| 03_httpx_missing_trust_env | httpx-trust-env-socks-proxy | True | **False** | True | 2315 |
| 04_clean_refactor | none | False | **False** | True | 2884 |

- **Recall: 67% (2/3)** — модель пропустила баг #3 (httpx `trust_env`), не сгенерировав ничего с ключевыми словами `trust_env`/`proxy`/`SOCKS`; реальный miss модели, не артефакт keyword-matching (проверено вручную — модель действительно не отметила это ни как баг, ни в рекомендациях).
- **False positive rate: 0% (0/1)** — чистая фикстура не породила выдуманных проблем.
- **Latency p50/p95/p99: 2845ms / 3476ms / 3559ms**
- **Cost за прогон (среднее): 0.0457₽**
- **% успешных прогонов: 100%**
- **RAG-индекс content-hash: `53b73380a53c`** (sha256[:12] от `index_project_proxy.json`) — день 33 должен пересчитать эти числа после пересборки корпуса, иначе baseline протухнет молча.

**`score` подкоманда проверена вживую:** `python -m agent_web.services.review score eval-04_clean_refactor 5` → `data/review_metrics.jsonl` содержит `"human_score": 5` на этой записи.

## Что НЕ проверено (и почему)

- **Живой триггер PR → комментарий бота на GitHub.** Требует: (а) реальный PR в `github.com/VladislavEllert/AIAdventChallange`, (б) GitHub Secret `PROXYAPI_KEY`, добавленный юзером руками (Settings → Secrets and variables → Actions — вне доступа агента). По плану это явно шаг **35.5** («слак дня 32»), не в скоуп этой фазы. YAML-синтаксис workflow проверен (`python -c "import yaml; yaml.safe_load(...)"` → OK), логика шагов проверена чтением.
- **Playwright e2e.** Фаза чисто backend/CLI — не тронут ни `chat.py`, ни фронтенд, UI-поверхности нет. По правилу skill `e2e-web` — пропущено осознанно, не забыто.

## Что не получилось сделать красиво

Первая попытка 32.0 — объявить `agent-cli` как относительную `file://`-зависимость прямо в `agent-web/pyproject.toml`, чтобы формальный граф зависимостей был самодостаточным. Pip 25 такое отклоняет («non-local file URIs are not supported on this platform») — переменные вида `${PROJECT_ROOT}` в dependency-спецификаторах pip не подставляет, а голый относительный путь в `file://` тоже не резолвится надёжно. Откатился на вариант, который явно разрешён планом («или иначе гарантировать совместную установку») — установка обоих пакетов вместе везде, документирующий комментарий вместо рабочей, но хрупкой декларации.
