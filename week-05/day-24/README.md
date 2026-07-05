# Day 24 — Citations, Sources & Anti-Hallucination

## ⭐ Main Code

| File | What it does |
|------|-------------|
| [`agent-web/agent_web/routers/chat.py`](../../agent-web/agent_web/routers/chat.py) | Don't-know gate (`best_score < 0.55`); `sources` SSE event; citation instruction in system prompt |
| [`agent-web/frontend/src/components/chat/SourcesBlock.tsx`](../../agent-web/frontend/src/components/chat/SourcesBlock.tsx) | Sources list with clickable URLs, score badges, expandable quotes |
| [`agent-web/frontend/src/stores/useChatStore.ts`](../../agent-web/frontend/src/stores/useChatStore.ts) | `Source[]` on Message, `appendSources()` action |
| [`agent-web/frontend/src/api/chat.ts`](../../agent-web/frontend/src/api/chat.ts) | `onSources` + `onRagMeta` callbacks, parse `sources` / `rag_meta` SSE events |
| [`agent-web/frontend/src/components/chat/MessageBubble.tsx`](../../agent-web/frontend/src/components/chat/MessageBubble.tsx) | Renders `SourcesBlock` under assistant message |
| [`agent-web/rag_eval/run_eval.py`](../../agent-web/rag_eval/run_eval.py) | `--day 24`: sources-in-answer check + don't-know gate test |
| [`agent-web/rag_eval/results_day23.md`](../../agent-web/rag_eval/results_day23.md) | те же 10 вопросов дня 23 (с sources/цитатами) — фичи дня 24 уже покрыты этим прогоном |

## Task

RAG must return: answer + sources (URL + section + chunk_id) + quotes. Verify on 10 questions. Anti-hallucination: if best score < threshold → "I don't know" without calling LLM.

## What was done

**Don't-know gate:**
- Before calling LLM: check `rag_meta['best_score'] < THRESHOLD_ANSWER` (0.55)
- If triggered: emit "I don't have information…" + closest topic hint, skip LLM call
- Verified: "What is the current weather in Moscow today?" → score=0.490 → gate triggered ✅

**Sources SSE event (`sources`):**
- Emitted right after retrieval, before LLM streams the answer
- Payload: list of `{source, section, chunk_id, quote[:300], score}`
- Frontend receives it via `onSources` callback → `appendSources(assistantId, sources)` → stored on Message

**Citation system prompt injection:**
```
[RAG MODE] Answer ONLY using the excerpts below.
After your answer, add a '**Sources:**' section listing the URLs used.
Include a short quote from each source that supports your answer.
If the excerpts do not contain the answer, say you don't know.
```

**UI — SourcesBlock under each RAG assistant message:**
- Collapsible list: `▸ Section name — score badge`
- Click to expand: chunk_id + blockquote excerpt
- Clickable URL → opens handbook page
- Filter badge: `📚 RAG raw=20 → kept=N → used=5 | best=0.XXX`
- Rewritten query shown (truncated, full on hover)

## Run eval

Отдельного прогона дня 24 нет — вопросы дублируют день 23, а прогон дня 23 (`results_day23.md`)
уже включает sources/цитаты в каждом ответе, так что демонстрирует фичи дня 24 без повтора.

```bash
cd agent-web
.venv/bin/python3 rag_eval/run_eval.py --day 23
# → rag_eval/results_day23.md
```

## Key observation

Every RAG answer on in-scope questions contains `**Sources:**` section with handbook URLs. Out-of-scope question ("weather in Moscow") triggers don't-know gate at score=0.490 < 0.55 — LLM never called, no hallucination.
