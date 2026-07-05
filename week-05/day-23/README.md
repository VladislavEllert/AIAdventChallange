# Day 23 — Reranking & Filtering

## ⭐ Main Code

| File | What it does |
|------|-------------|
| [`agent-web/agent_web/routers/chat.py`](../../agent-web/agent_web/routers/chat.py) | Query rewrite via LLM before retrieval; filter stats in SSE `rag_meta` event |
| [`agent-web/frontend/src/stores/useChatStore.ts`](../../agent-web/frontend/src/stores/useChatStore.ts) | `RagMeta` type + `appendRagMeta()` action on Message |
| [`agent-web/frontend/src/components/chat/SourcesBlock.tsx`](../../agent-web/frontend/src/components/chat/SourcesBlock.tsx) | Filter badge: `raw → kept → used` + best score + rewritten query |
| [`agent-web/rag_eval/run_eval.py`](../../agent-web/rag_eval/run_eval.py) | `--day 23` mode: rewrite ON + filter stats in results |
| [`agent-web/rag_eval/results_day23.md`](../../agent-web/rag_eval/results_day23.md) | 10 questions × (without RAG / with RAG+rewrite+filter) |

## Task

Add a second stage after retrieval: query rewrite + relevance threshold filter. Compare quality **with filter vs without filter** (both arms use RAG). Set top-K before/after filtering.

## What was done

**Query rewrite:**
- Short LLM call before embedding: translate to English (docs are English-only) + expand abbreviations/synonyms
- Bug found & fixed: `rag_eval/run_eval.py`'s rewrite prompt didn't translate, only `chat.py`'s (prod) did. Verified impact directly: same Russian question scored 0.64 with a broken top-5 (wrong chunks) before the fix, 0.80 with the correct chunk ranked #1 after.
- Fallback to original query on error

**Filter pipeline (heuristic threshold, not a cross-encoder reranker):**
- `top_k_raw=20` candidates → cosine score filter → `top_k_final=5` used
- Prod default: `THRESHOLD=0.5`, `THRESHOLD_ANSWER=0.55` (`agent_web/services/rag/config.py`)
- Calibrated by hand against 6 real handbook questions + 4 irrelevant ones (varying difficulty: dogs/cats — HR-flavored nonsense scoring 0.59–0.66 — down to totally unrelated cooking question at 0.42). `threshold=0.65` is the value used for the eval comparison below — it's the cleanest cut point found (kept=0 for all 4 irrelevant, kept>0 for all 6 real questions).
- `rag_meta` SSE event carries: `raw`, `kept`, `final`, `best_score`, `rewritten_query`

**UI (filter badge in SourcesBlock):**
- `raw=20 → kept=N → used=5 | best=0.XXX`
- Rewritten query shown on hover/truncated

## Run eval

```bash
cd agent-web
.venv/bin/python3 rag_eval/run_eval.py --day 23
# → rag_eval/results_day23.md — 10 questions, each run twice: RAG with threshold=0.0 (no filter) vs RAG with threshold=0.65 (filtered)
```

## Key observations

- Filter measurably cuts context: `kept` drops from 20→4-20 on real questions, and to **0** on all 4 irrelevant/off-topic questions (dogs, cat breed, cooking, dress code).
- On this question set, the **final answer text barely changes** with vs without the filter — query rewrite + the "answer only from context" system prompt already made the LLM say "I don't know" on irrelevant questions even with 20 unfiltered chunks in context. The filter's real value here: it makes that rejection **deterministic** (doesn't rely on the LLM behaving) and **cheaper** (0 chunks in context instead of 5 irrelevant ones for the off-topic questions).
- Cross-lingual embedding is a real risk: Russian query vs English docs tanks both score and *ranking order* — a pure similarity threshold can't fix bad ranking, only trims the tail. Translating the query first (part of the rewrite step) is what actually fixes recall.
