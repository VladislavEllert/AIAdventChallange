"""Tests for MCP client — schema conversion (no network)."""
from agent_web.services.mcp_client import _to_openai_schema, TOOL_LABELS


class FakeTool:
    name = "test_tool"
    description = "Does something useful"
    inputSchema = {"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]}


def test_schema_conversion_structure():
    schema = _to_openai_schema(FakeTool())
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "test_tool"
    assert schema["function"]["description"] == "Does something useful"
    assert "q" in schema["function"]["parameters"]["properties"]


def test_schema_conversion_no_input_schema():
    class NoSchema:
        name = "bare_tool"
        description = "Bare"
        inputSchema = None
    schema = _to_openai_schema(NoSchema())
    assert schema["function"]["parameters"] == {"type": "object", "properties": {}}


def test_tool_labels_present():
    assert "web_search" in TOOL_LABELS
    assert "get_moex_quote" in TOOL_LABELS
    assert "get_moex_summary" in TOOL_LABELS
