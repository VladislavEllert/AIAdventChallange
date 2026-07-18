<!-- source: agent-web/agent_web/services/commands.py | title: commands.py -->

"""Slash-command registry — day 31+.

ONLY for new commands (/help now, /support and /ritual on later days). The
four pre-existing commands hardcoded in chat.py (/mcp, /history, /ping,
/analyze) are NOT migrated here — that file is a hot path and migrating
working code for zero behavioral gain is out of scope (see plan's "Out of
scope"). This registry is checked in chat.py BEFORE those legacy branches.
"""
from dataclasses import dataclass
from typing import Callable, Iterator

# A handler yields (event_name, data) pairs — chat.py wraps them in its own
# SSE framing (_sse_event) so this module has no FastAPI/SSE-format coupling.
CommandHandler = Callable[..., Iterator[tuple[str, dict]]]


@dataclass
class Command:
    name: str
    description: str
    handler: CommandHandler


_REGISTRY: dict[str, Command] = {}


def register(name: str, description: str, handler: CommandHandler) -> None:
    _REGISTRY[name.lower()] = Command(name=name, description=description, handler=handler)


def resolve(msg: str) -> Command | None:
    """Return the Command matching msg's first word, or None (including for empty/non-slash input)."""
    if not msg:
        return None
    stripped = msg.strip()
    if not stripped.startswith("/"):
        return None
    first_word = stripped.split(maxsplit=1)[0].lower()
    return _REGISTRY.get(first_word)


def registered_commands() -> list[Command]:
    return list(_REGISTRY.values())
