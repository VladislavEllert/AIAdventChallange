<!-- source: week-05/day-22/README.md | title: README.md -->

# Day 22 — First RAG Query + Comparison

**Видео (неделя 5, все дни):** [▶ Google Drive](https://drive.google.com/drive/folders/1Buhxb6gJ6stIYDTxpYsWL0Ce9rAinH3H?usp=share_link)


## ⭐ Main Code

| File | What it does |
|------|-------------|
| [`agent-web/agent_web/schemas/chat.py`](../../agent-web/agent_web/schemas/chat.py) | `ChatRequest` + `use_rag: bool` field |
| [`agent-web/agent_web/dependencies.py`](../../agent-web/agent_web/dependencies.py) | Singleton `get_rag_index()` — lazy-loads `index_fixed.json` |
| [`agent-web/agent_web/routers/chat.py`](../../agent-web/agent_web/routers/chat.py) | RAG branch: retrieve → build context → stream with `working_context` |
| [`agent-web/frontend/src/stores/useAppStore.ts`](../../agent-web/frontend/src/stores/useAppStore.ts) | `ragEnabled` state + `setRagEnabled` |
| [`agent-web/frontend/src/components/layout/MainLayout.tsx`](../../agent-web/frontend/src/components/layout/MainLayout.tsx) | RAG toggle button in top bar |
| [`agent-web/frontend/src/api/chat.ts`](../../agent-web/frontend/src/api/chat.ts) | `use_rag` field passed in request body |
| [`agent-web/rag_eval/questions.json`](../../agent-web/rag_eval/questions.json) | 10 control questions with expectations + expected sources |
| [`agent-web/rag_eval/run_eval.py`](../../agent-web/rag_eval/run_eval.py) | Runs 10 questions in both modes → `results_day22.md` |
| [`agent-web/rag_eval/results_day22.md`](../../agent-web/rag_eval/results_day22.md) | Evaluation results: without RAG vs with RAG |

## Task

Build a RAG query pipeline: question → chunk retrieval → context injection → LLM. Compare responses with/without RAG. Bonus: 10 control questions with expectations and sources.

## What was done

**Backend:**
- `ChatRequest.use_rag: bool = False` — toggle per request
- `get_rag_index()` singleton in `dependencies.py` — loads `index_fixed.json` once
- RAG branch in `chat.py`: retrieve top-5 chunks → numbered context with source/section → inject via `agent._build_messages(msg, working_context=...)` → stream response
- Baseline path (without RAG) unchanged

**Frontend:**
- `ragEnabled` persisted in `useAppStore`
- `◇ RAG` / `◈ RAG` toggle button in top bar (lights up when on)
- `use_rag` passed in every chat request body

**Evaluation:**
- 10 questions covering: PTO, values, DRI, code review, parental leave, iteration, anti-harassment, reviewer values, async comms, RCA
- `run_eval.py` hits both modes → `results_day22.md`

## Run eval

```bash
cd agent-web
.venv/bin/python3 rag_eval/run_eval.py
# → rag_eval/results_day22.md
```

## Key observation

Without RAG on Q2 (GitLab values): generic list, wrong order.
With RAG: exact CREDIT acronym, emoji icons from the actual handbook page.
Hallucinations → facts.
