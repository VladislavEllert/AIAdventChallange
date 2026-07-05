# Day 25 — RAG + Task Memory (production-like chat)

**Видео (неделя 5, все дни):** [▶ Google Drive](https://drive.google.com/drive/folders/1Buhxb6gJ6stIYDTxpYsWL0Ce9rAinH3H?usp=share_link)


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

**Task state extraction (code owns accumulation, LLM only proposes a delta):**
- After each user message (RAG mode): short LLM call (`gpt-4o-mini`, `max_tokens=300`, `response_format=json_object`)
- Input: last 12 messages from `Memory.short_term` + the CURRENT goal/facts/constraints
- Output: `{goal, new_facts, new_constraints}` — only what's NEW in this turn
- Merge happens in Python (`extract_task_state()`): `goal` is set once and frozen (never overwritten once non-empty); `new_facts`/`new_constraints` are appended with exact-string dedup
- Stored in `Memory.working` (already declared in dataclass, was unused before)
- Fallback: return current state unchanged on any error

**Why the merge is deterministic, not LLM-driven:** first version asked the LLM to re-derive the *whole* `{goal, clarified_facts, constraints}` state every turn from a short window of recent messages. In testing this drifted badly — `goal` kept jumping to whatever the last 1-2 exchanges were about (e.g. locked onto "power harassment" after two Q&A turns on that topic, discarding the real conversation-level goal), and facts got polluted with GitLab domain knowledge from the assistant's own answers instead of things the user actually said. Fix: the LLM never sees or restates the accumulated state as a whole — it only reports the delta for the current turn, and Python appends it. `clarified_facts` covers both (1) facts about the user themselves and (2) a short label for each topic they asked about, so "what the user already clarified" is visibly non-empty and growing across a long conversation, not just personal facts.

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

| Scenario | Sources present | Goal | Notes |
|---|---|---|---|
| A: New employee onboarding | 9/10 | frozen from turn 2: "успешное начало работы в GitLab" | 1 honest "I don't know" despite score > threshold |
| B: Engineering career growth | 7/10 | frozen from turn 2: "развивать карьеру в GitLab" | 3 turns "I don't know" — those topics (performance reviews, underperformance handling, mgmt principles) genuinely aren't in the loaded handbook corpus |

```bash
cd agent-web
.venv/bin/python3 rag_eval/run_eval.py --day 25
# → rag_eval/results_day25.md
```

## SSE order (Day 25)

`sources` → `rag_meta` → **`task_state`** → `chunk` × N → `usage` → `done`

## Key observation

`goal` is set once (turn 2 in both scenarios) and stays frozen for the rest of a 10-turn conversation — it does not drift to whatever topic the last question happened to be about. `clarified_facts` grows by one entry almost every turn (both self-facts and topic labels), so by turn 10 it visibly reflects "everything the user has clarified" instead of staying at 1-2 items. `constraints` catches instructions like "answer only in Russian, max 3 sentences" even when they're a side remark attached to an unrelated question, and persists them to the end. "I don't know" responses (retrieved score above threshold but content genuinely absent from the corpus) correctly have no sources — anti-hallucination from day 24 still holds under task memory.
