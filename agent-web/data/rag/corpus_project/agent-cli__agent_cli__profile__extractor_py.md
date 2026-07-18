<!-- source: agent-cli/agent_cli/profile/extractor.py | title: extractor.py -->

from agent_cli.llm.provider import LLMProvider
from agent_cli.config import DEFAULT_MODEL

_LAYERS = ("persona", "style", "rules", "stack", "interests")

_SYSTEM = """Определи, в какой слой профиля добавить факт о пользователе.
Слои:
- persona: кто пользователь, роль, цели
- style: стиль общения, предпочтения формата
- rules: запреты, ограничения, обязательные правила
- stack: технический стек, языки, фреймворки, инструменты
- interests: хобби, интересы, предпочтения вне работы

Ответь ТОЛЬКО одним словом из списка: persona, style, rules, stack, interests"""


def route_fact(fact: str, provider: LLMProvider, model: str = DEFAULT_MODEL) -> str:
    """Returns which profile layer this fact belongs to."""
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": f"Факт: {fact}"},
    ]
    result = provider.chat(messages, model).strip().lower()
    return result if result in _LAYERS else "persona"
