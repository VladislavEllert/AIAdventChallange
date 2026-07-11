"""
Task state extraction from conversation history (Day 25).
Extracts: goal, clarified_facts, constraints.
Stored in Memory.working per session.
"""
import json

# Fallback when the caller doesn't pass an active model (e.g. old call sites).
DEFAULT_MODEL = "ollama/qwen3:4b"

_SYSTEM = (
    "You track incremental task state for a long conversation. You are given the "
    "CURRENT GOAL (may be empty) and the MOST RECENT messages only — not the full "
    "history. Extract ONLY what is NEW in these recent messages, as JSON with keys: "
    "\"goal\" (string: set ONLY if CURRENT GOAL is empty. Infer the user's overall "
    "objective for the WHOLE conversation from the THEME connecting these messages — "
    "it does not need to be explicitly stated as 'I want/I am', a cluster of related "
    "questions is enough (e.g. several questions about engineering career growth → "
    "goal='growing an engineering career at GitLab'). Otherwise return an empty "
    "string — do NOT restate or replace an existing goal, do NOT set the goal to "
    "just the topic of the single latest question if earlier messages in this batch "
    "point to a broader theme), "
    "\"new_facts\" (list of strings: what the user has CLARIFIED in these messages — "
    "this covers two things: (1) facts about THEMSELVES or their own situation — role, "
    "timeline, background, location, a side comment, a hobby or plan mentioned in "
    "passing (users often bury such a detail inside an unrelated question, e.g. "
    "'What is X? Also, I bike to work, is there parking?' contains 'user bikes to "
    "work' — scan the ENTIRE message, not just its main question); AND (2) the "
    "specific topic/question they asked about in THIS turn, as a short label (e.g. "
    "'спросил про срок ответа ревьюера на code review', 'спросил про декретный "
    "отпуск') so later turns don't lose track of what's already been covered. "
    "STRICT RULE: record that the user asked about a topic, but do NOT copy the "
    "assistant's full domain answer/policy details into this list — one short "
    "label per topic, not the answer content. Do NOT repeat or rephrase anything "
    "already in CURRENT FACTS below — if the user just restates something already "
    "known, return an empty list), "
    "\"new_constraints\" (list of strings: NEW limits, requirements, or terms the "
    "user fixed in these messages — e.g. 'answer only in Russian', 'keep answers "
    "under 3 sentences', 'always cite sources'. CHECK EVERY user message in this "
    "window carefully for such an instruction, even if it's a side remark attached "
    "to an unrelated question — this field is just as important as new_facts, do "
    "not skip it. Do NOT repeat or rephrase anything already in CURRENT CONSTRAINTS "
    "below). "
    "Write facts/constraints in Russian if the conversation is in Russian. "
    "If nothing new, still return valid JSON with all three keys present "
    "(empty string / empty lists) — never return an empty object. "
    "Be concise — max 15 words per item. Return ONLY valid JSON, no explanation."
)


def extract_task_state(provider, history: list[dict], current: dict, model: str | None = None) -> dict:
    """Ask the LLM for only the NEW goal/facts/constraints in the recent turn, then
    merge that delta into `current` in code — the LLM never re-derives or overwrites
    the accumulated state, which avoids goal/fact drift across topic changes.

    `model` should be the session's active chat model (via DispatchProvider.client_for)
    so this stays local when the user is on a local model — otherwise a RAG chat on
    Ollama would silently still call the cloud for task-state extraction."""
    current = current or {"goal": "", "clarified_facts": [], "constraints": []}
    if not history:
        return current

    state_line = (
        f"CURRENT GOAL: {current.get('goal') or '(empty)'}\n"
        f"CURRENT FACTS: {json.dumps(current.get('clarified_facts', []), ensure_ascii=False)}\n"
        f"CURRENT CONSTRAINTS: {json.dumps(current.get('constraints', []), ensure_ascii=False)}"
    )

    try:
        if hasattr(provider, "client_for"):
            client, bare_model = provider.client_for(model or DEFAULT_MODEL)
        else:
            client, bare_model = provider.client, (model or DEFAULT_MODEL)
        resp = client.chat.completions.create(
            model=bare_model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": state_line},
                *history,
            ],
            max_tokens=300,
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content.strip()
        parsed = json.loads(raw)

        goal = current.get("goal") or str(parsed.get("goal", ""))

        facts = list(current.get("clarified_facts", []))
        for f in parsed.get("new_facts", []):
            f = str(f)
            if f and f not in facts:
                facts.append(f)

        constraints = list(current.get("constraints", []))
        for c in parsed.get("new_constraints", []):
            c = str(c)
            if c and c not in constraints:
                constraints.append(c)

        return {"goal": goal, "clarified_facts": facts, "constraints": constraints}
    except Exception:
        return current


def format_task_state_block(task_state: dict) -> str:
    """Format task state as a system prompt injection block."""
    if not task_state.get("goal"):
        return ""
    lines = [f"[TASK MEMORY]\nGoal: {task_state['goal']}"]
    if task_state.get("clarified_facts"):
        lines.append("Clarified: " + "; ".join(task_state["clarified_facts"]))
    if task_state.get("constraints"):
        lines.append("Constraints: " + "; ".join(task_state["constraints"]))
    return "\n\n" + "\n".join(lines)
