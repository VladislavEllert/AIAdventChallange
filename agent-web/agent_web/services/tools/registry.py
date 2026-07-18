"""Day 34: tool registry — local (non-MCP) tools the chat tool-calling loop can
call directly, gated by danger.py + confirm.py.

Mirrors the shape of MCP tool schemas (`{"type": "function", "function": {...}}`)
so chat.py can merge these into the same `tool_schemas` list it already builds
from `get_tools_sync()` and drive both through one loop.
"""
from dataclasses import dataclass
from typing import Any, Callable

DangerLevel = str  # "safe" | "dangerous" — see tools/danger.py for the source of truth


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON schema for the function's arguments
    execute: Callable[..., str]  # (**kwargs) -> str result
    danger_level: DangerLevel = "safe"

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


_REGISTRY: dict[str, Tool] = {}


def register(tool: Tool) -> None:
    _REGISTRY[tool.name] = tool


def get(name: str) -> Tool | None:
    return _REGISTRY.get(name)


def get_schemas() -> list[dict]:
    return [t.schema() for t in _REGISTRY.values()]


def registered_names() -> list[str]:
    return list(_REGISTRY.keys())


def _reset_registry_for_tests() -> None:
    """Test-only escape hatch — production code never calls this."""
    _REGISTRY.clear()
