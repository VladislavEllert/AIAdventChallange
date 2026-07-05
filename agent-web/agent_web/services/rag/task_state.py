"""
Task state extraction from conversation history (Day 25).
Extracts: goal, clarified_facts, constraints.
Stored in Memory.working per session.
"""
import json

MODEL = "openai/gpt-4o-mini"

_SYSTEM = (
    "Extract the task state from this conversation history as JSON with exactly these keys: "
    "\"goal\" (string: the user's main objective in this conversation, empty string if unclear), "
    "\"clarified_facts\" (list of strings: specific facts/details the user has established), "
    "\"constraints\" (list of strings: limits, requirements, or terms the user fixed). "
    "Be concise — max 15 words per item. Return ONLY valid JSON, no explanation."
)


def extract_task_state(provider, history: list[dict], current: dict) -> dict:
    """Short LLM call to extract task state from recent history. Falls back to current on error."""
    if not history:
        return current or {"goal": "", "clarified_facts": [], "constraints": []}

    try:
        resp = provider.client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM},
                *history[-6:],
            ],
            max_tokens=200,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        parsed = json.loads(raw)
        return {
            "goal": str(parsed.get("goal", "")),
            "clarified_facts": [str(x) for x in parsed.get("clarified_facts", [])],
            "constraints": [str(x) for x in parsed.get("constraints", [])],
        }
    except Exception:
        return current or {"goal": "", "clarified_facts": [], "constraints": []}


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
