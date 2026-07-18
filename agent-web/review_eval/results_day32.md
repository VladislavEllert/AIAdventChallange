# День 32 — AI-ревью PR: eval-результаты

## Прогон 1 (день 32 baseline, до пересборки индекса дня 33)

Прогон: 2026-07-18 20:54:22

Модель: `openai/gpt-4o-mini`, prompt_version: `v1`

RAG-индекс `index_project_proxy.json` content-hash (sha256[:12]): `53b73380a53c` — день 33 пересобирает корпус; если этот хэш изменился, а числа ниже не пересчитаны, baseline устарел.

### Метрики

- Recall (баги найдены / всего багов): **67%** (2/3)
- False positive rate (чистая фикстура ошибочно помечена): **0%** (0/1)
- Latency p50 / p95 / p99: 2845ms / 3476ms / 3559ms
- Cost за прогон (среднее): 0.0457₽
- % успешных прогонов: 100%

### Детали по фикстурам

| fixture | bug_class | expect_flag | flagged | ok | latency_ms |
|---|---|---|---|---|---|
| 01_dotenv_wrong_env | dotenv-wrong-env-resolution | True | True | True | 3580 |
| 02_isinstance_breaks_streaming | isinstance-breaks-dispatch-wrapper | True | True | True | 2806 |
| 03_httpx_missing_trust_env | httpx-trust-env-socks-proxy | True | False | True | 2315 |
| 04_clean_refactor | none | False | False | True | 2884 |

---

## Прогон 2 (день 33, после пересборки индекса с faq.md, 194→207 чанков)

Прогон: 2026-07-18 21:34:39

Модель: `openai/gpt-4o-mini`, prompt_version: `v1`

RAG-индекс `index_project_proxy.json` content-hash (sha256[:12]): `4f7971c234d9` — индекс изменился (был `53b73380a53c`), ожидаемо: корпус пересобран (155 файлов, +`corpus_project/faq.md`), 207 чанков (было 194).

### Метрики

- Recall (баги найдены / всего багов): **33%** (1/3)
- False positive rate (чистая фикстура ошибочно помечена): **0%** (0/1)
- Latency p50 / p95 / p99: 2507ms / 3270ms / 3370ms
- Cost за прогон (среднее): 0.0374₽
- % успешных прогонов: 100%

### Детали по фикстурам

| fixture | bug_class | expect_flag | flagged | ok | latency_ms |
|---|---|---|---|---|---|
| 01_dotenv_wrong_env | dotenv-wrong-env-resolution | True | True | True | 3395 |
| 02_isinstance_breaks_streaming | isinstance-breaks-dispatch-wrapper | True | False | True | 2344 |
| 03_httpx_missing_trust_env | httpx-trust-env-socks-proxy | True | False | True | 2559 |
| 04_clean_refactor | none | False | False | True | 2456 |

### Note

Recall dropped 67%→33% (fixture 02 stopped being flagged) between прогон 1 и 2. Same
model/prompt, different index content (FAQ added, chunk count 194→207, likely shifted
retrieval — FAQ chunks may now outrank code chunks for some queries) plus normal LLM
run-to-run variance at temperature>0. Not investigated further — out of scope for день 33
(index rebuild was the required action, not review-quality tuning); flagging for whoever
picks up день 32 follow-up or день 34/35.

---

## Прогон 3 (prompt_version=`v2_strict` — day 35 comparison vs v1 baseline)

Прогон: 2026-07-18 23:02:57

Модель: `openai/gpt-4o-mini`, prompt_version: `v2_strict`

RAG-индекс `index_project_proxy.json` content-hash (sha256[:12]): `4f7971c234d9` — день 33 пересобирает корпус; если этот хэш изменился, а числа ниже не пересчитаны, baseline устарел.

### Метрики

- Recall (баги найдены / всего багов): **100%** (3/3)
- False positive rate (чистая фикстура ошибочно помечена): **0%** (0/1)
- Latency p50 / p95 / p99: 2688ms / 4360ms / 4593ms
- Cost за прогон (среднее): 0.0538₽
- % успешных прогонов: 100%

### Детали по фикстурам

| fixture | bug_class | expect_flag | flagged | ok | latency_ms |
|---|---|---|---|---|---|
| 01_dotenv_wrong_env | dotenv-wrong-env-resolution | True | True | True | 4651 |
| 02_isinstance_breaks_streaming | isinstance-breaks-dispatch-wrapper | True | True | True | 2292 |
| 03_httpx_missing_trust_env | httpx-trust-env-socks-proxy | True | True | True | 2715 |
| 04_clean_refactor | none | False | False | True | 2661 |

---

## Прогон 4 (prompt_version=`v1` — day 35 comparison — v1 rerun for fair same-session baseline)

Прогон: 2026-07-18 23:03:18

Модель: `openai/gpt-4o-mini`, prompt_version: `v1`

RAG-индекс `index_project_proxy.json` content-hash (sha256[:12]): `4f7971c234d9` — день 33 пересобирает корпус; если этот хэш изменился, а числа ниже не пересчитаны, baseline устарел.

### Метрики

- Recall (баги найдены / всего багов): **33%** (1/3)
- False positive rate (чистая фикстура ошибочно помечена): **0%** (0/1)
- Latency p50 / p95 / p99: 2815ms / 3358ms / 3427ms
- Cost за прогон (среднее): 0.0385₽
- % успешных прогонов: 100%

### Детали по фикстурам

| fixture | bug_class | expect_flag | flagged | ok | latency_ms |
|---|---|---|---|---|---|
| 01_dotenv_wrong_env | dotenv-wrong-env-resolution | True | True | True | 3445 |
| 02_isinstance_breaks_streaming | isinstance-breaks-dispatch-wrapper | True | False | True | 2448 |
| 03_httpx_missing_trust_env | httpx-trust-env-socks-proxy | True | False | True | 2867 |
| 04_clean_refactor | none | False | False | True | 2763 |

### v1 vs v2_strict — day 35.6 comparison

Прогоны 3/4 ran back-to-back, same session, same RAG index (`4f7971c234d9`), same model
— isolates the prompt as the only variable (unlike прогон 1→2, which conflated an index
rebuild with normal LLM variance).

| prompt_version | recall | FP-rate | latency p50 | cost/run |
|---|---|---|---|---|
| `v1` | 33% (1/3) | 0% (0/1) | 2815ms | 0.0385₽ |
| `v2_strict` | **100% (3/3)** | 0% (0/1) | 2688ms | 0.0538₽ |

`v2_strict` caught fixture 03 (httpx `trust_env`/SOCKS) — the one bug class every prior
`v1` run (прогон 1 and прогон 4) missed — by naming that exact failure shape explicitly in
the system prompt instead of leaving the model to infer it from a generic "find bugs"
instruction. FP-rate held at 0% (didn't start over-flagging the clean fixture to get
there), latency was flat, cost per run rose ~40% (0.0385₽→0.0538₽, from the added
checklist tokens) — a real but small trade for a 3x recall gain on 4 fixtures. Caveat:
n=4 fixtures is too small to claim this generalizes past these specific bug shapes; `v2_strict`
explicitly enumerates bug shapes drawn from THIS project's history, so it may be
overfit to these fixtures rather than a general "be more careful" improvement. Not
promoted to the CI default (`PROMPT_VERSION` stays `v1`) — that's a call for whoever owns
review-quality tuning next, this just proves the comparison mechanism works.
