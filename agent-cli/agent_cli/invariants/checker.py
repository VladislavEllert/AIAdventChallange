import re
from agent_cli.llm.provider import LLMProvider
from agent_cli.config import DEFAULT_MODEL

_CHECK_SYSTEM = """Проверь, нарушает ли ответ ИИ-ассистента какой-либо из инвариантов.
Инварианты — жёсткие правила, которые НЕЛЬЗЯ нарушать ни при каких условиях.

Если нарушение есть — ответь строго в формате:
НАРУШЕНИЕ: <формулировка нарушенного инварианта>

Если всё в порядке — ответь одним словом:
ОК"""


def check_code(response: str, invariants: list[str]) -> tuple[bool, str]:
    """Fast keyword pre-check before hitting LLM."""
    resp_lower = response.lower()
    for inv in invariants:
        # Extract forbidden words/phrases after "запрет", "запрещ", "без", "не использ"
        forbid_words = re.findall(
            r"(?:запрет\w*|запрещ\w*|не использ\w*)\s+([\w-]+)", inv.lower()
        )
        for word in forbid_words:
            if len(word) > 3 and word in resp_lower:
                return False, f"Keyword violation of invariant: '{inv}'"
    return True, ""


def check_llm(
    response: str,
    invariants: list[str],
    provider: LLMProvider,
    model: str = DEFAULT_MODEL,
) -> tuple[bool, str]:
    """LLM-based invariant check. Returns (ok, violation_description)."""
    if not invariants:
        return True, ""
    inv_text = "\n".join(f"- {inv}" for inv in invariants)
    messages = [
        {"role": "system", "content": _CHECK_SYSTEM},
        {"role": "user", "content": f"Инварианты:\n{inv_text}\n\nОтвет ассистента:\n{response}"},
    ]
    result = provider.chat(messages, model).strip()
    if result.upper().startswith("НАРУШЕНИЕ"):
        violation = result.split(":", 1)[1].strip() if ":" in result else result
        return False, violation
    return True, ""
