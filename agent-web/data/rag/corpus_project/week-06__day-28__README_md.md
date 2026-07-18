<!-- source: week-06/day-28/README.md | title: README.md -->

# Day 28 — Local LLM + RAG

## Видео

[Видео дня](https://drive.google.com/drive/folders/1clLB0Q5h68tDx2e6xf_AcQwMHgRS9KW4?usp=share_link) (папка со всеми видео недели 6)

## ⭐ Main Code

| File | What it does |
|------|-------------|
| [`agent-web/rag_eval/run_eval.py`](../../agent-web/rag_eval/run_eval.py) | Comparison script, now routed through `DispatchProvider` with a `--model` flag |
| [`agent-web/rag_eval/results_day28.md`](../../agent-web/rag_eval/results_day28.md) | Real run: 10 questions, `ollama/qwen3:4b`, plain vs RAG |
| [`agent-web/agent_web/routers/chat.py`](../../agent-web/agent_web/routers/chat.py) | Query-rewrite now skips for `ollama/*` models (see bug below) |

## Task

RAG fully local — retrieval already was (embeddings via Ollama since day 21), generation now
routed through the active model, so `ollama/qwen3:4b` + RAG needs zero internet. Compare local
vs cloud.

## What was done

RAG generation already flowed through `agent.model` (`chat.py:366`) — nothing to change there,
day 27's dispatcher handles it. What needed real work: two call sites still assumed a cloud
model and would have silently reached out to ProxyAPI even in a "fully local" RAG session:
query rewrite (`chat.py:269`) and task-state extraction (`task_state.py`, fixed in day 27
already via `client_for(model)`). This day closes the query-rewrite gap.

**One with/without-RAG comparison, on the local model, per your request — not an extended
analysis, the numbers are in `results_day28.md` for you to judge.** Ran the same 10 questions
from `questions.json` (day 22's set) against `ollama/qwen3:4b`, both with and without RAG
context, plus the day-24 don't-know gate test.

## A real bug found running it (not glossed over)

Qwen3 is a "thinking" model — Ollama's OpenAI-compat endpoint returns its `<think>` reasoning
as a separate `reasoning` field, and `content` stays empty until reasoning finishes. First run
of the eval: **every single answer came back empty.** Traced it to query-rewrite and the
plain/RAG completion calls all capping `max_tokens` at 80–500 — nowhere near enough for Qwen3
to finish thinking on this build. Verified live, pushing the cap up to **1500 tokens still
didn't finish** a single short query-rewrite task. Tried the documented fixes (`think: false`
on both the OpenAI-compat and native `/api/chat` endpoints, the `/no_think` prompt convention) —
none of them suppressed reasoning on this Ollama build.

Fix applied: for `ollama/*` models, skip query-rewrite entirely (fall back to the raw question)
and don't cap `max_tokens` on the plain/RAG completion calls (mirrors what day 27's streaming
chat already does correctly — no cap there, which is why day 27's live chat test worked while
this script's capped calls didn't).

**This fix has a real, measurable cost:** query-rewrite exists specifically to translate
Russian questions to English before embedding search (the corpus is English GitLab Handbook).
Skipping it for local models means the raw Russian question gets embedded directly. Comparing
retrieval quality on Q1 across the two runs:

- **Cloud (day 22, `gpt-4o-mini`, rewrite ON):** retrieved chunks from `time-off-types` /
  `time-off` — the right sections.
- **Local (day 28, `qwen3:4b`, rewrite skipped):** best_score=0.643 (above the 0.5 threshold,
  so it didn't trigger the don't-know gate) but retrieved chunks from `communication`,
  `security`, `values`, `people-group` — **wrong sections.** The RAG answer correctly said "I
  don't know" (better than hallucinating), but only because retrieval missed, not because the
  pipeline is smarter locally.

Cross-lingual embedding search alone is noticeably weaker than embedding-search-after-English-
rewrite. That's the honest local-vs-cloud quality gap for this task — not a close call.

The don't-know gate itself still works correctly on the local model (out-of-domain weather
question: best_score=0.472, correctly triggered "I don't know").

## Verification

- `agent-web` pytest: 36/36 green (unchanged from day 27, this day's chat.py edit is
  additive/defensive — a guard clause, no new surface).
- Real run against the live Windows Ollama box, not mocked — see `results_day28.md` for full
  transcripts of all 10 questions × 2 modes.

## Honest gap

Only compared retrieval/answer *quality*, not latency, per your instruction to keep this to one
comparison. Speed/resource numbers (tok/s, VRAM) belong to day 29's optimization pass, where
they're the actual point.
