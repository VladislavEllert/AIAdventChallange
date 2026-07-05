# Day 25 — RAG + Task Memory (production-like chat)

## ⭐ Main Code

| File | What it does |
|------|-------------|
| [`agent-web/agent_web/services/rag/task_state.py`](../../agent-web/agent_web/services/rag/task_state.py) | `extract_task_state()` — short LLM call to extract `{goal, clarified_facts, constraints}` from history |
| [`agent-web/agent_web/routers/chat.py`](../../agent-web/agent_web/routers/chat.py) | RAG path: extract task state → store in `Memory.working` → inject into system prompt → `task_state` SSE event |
| [`agent-web/frontend/src/components/chat/TaskStateBlock.tsx`](../../agent-web/frontend/src/components/chat/TaskStateBlock.tsx) | Collapsible task memory badge under each RAG assistant message |
| [`agent-web/frontend/src/stores/useChatStore.ts`](../../agent-web/frontend/src/stores/useChatStore.ts) | `TaskState` type + `appendTaskState()` action on `Message` |
| [`agent-web/frontend/src/api/chat.ts`](../../agent-web/frontend/src/api/chat.ts) | `onTaskState` callback, parses `task_state` SSE event |
| [`agent-web/rag_eval/run_eval.py`](../../agent-web/rag_eval/run_eval.py) | `--day 25`: 2 multi-turn scenarios × 10 messages each with task state tracking |
| [`agent-web/rag_eval/results_day25.md`](../../agent-web/rag_eval/results_day25.md) | Results: sources per turn + task state evolution |

## Task

Build a production-like chat that combines RAG with task memory:
- Conversation history maintained across turns
- Each turn: RAG retrieval → context injection → answer with sources
- Task state tracked: goal, clarified facts, constraints
- Validate on 2 long scenarios (10–15 messages)

## What was done

**Task state extraction:**
- After each user message (RAG mode): short LLM call (`gpt-4o-mini`, `max_tokens=200`)
- Input: last 6 messages from `Memory.short_term`
- Output: `{goal, clarified_facts, constraints}` JSON
- Stored in `Memory.working` (already declared in dataclass, was unused before)
- Fallback: return current state unchanged on any error

**System prompt injection:**
```
[TASK MEMORY]
Goal: <user's main objective>
Clarified: <fact1>; <fact2>
Constraints: <c1>; <c2>
```
Injected before `[RAG MODE]` instruction, keeping task context persistent across turns.

**SSE event `task_state`:**
- Emitted after `rag_meta`, before `chunk` events
- Frontend: `onTaskState` callback → `appendTaskState(assistantId, ts)` → stored on `Message`

**UI — TaskStateBlock:**
- Collapsible badge under each RAG assistant message: `▸ 🎯 Task memory | <goal>`
- Expanded: Goal, Clarified facts, Constraints

**Multi-turn eval — 2 scenarios × 10 messages:**

| Scenario | Sources present | Notes |
|---|---|---|
| A: New employee onboarding | 10/10 ✅ | All in-scope questions answered with sources |
| B: Engineering career growth | 7/10 | 3 turns: "I don't know" (topics not in handbook = correct!) |

```bash
cd agent-web
.venv/bin/python3 rag_eval/run_eval.py --day 25
# → rag_eval/results_day25.md
```

## SSE order (Day 25)

`sources` → `rag_meta` → **`task_state`** → `chunk` × N → `usage` → `done`

## Key observation

Task state is extracted fresh every turn from the last 6 messages — so the `goal` field evolves as the conversation progresses. The assistant never loses the thread: conversation history is always passed in full to the LLM, and task state reinforces the current objective in the system prompt. "I don't know" responses (score > 0.55 but insufficient context) correctly have no sources — the citation instruction works.
