"""MCP client — connects to remote MCP server, fetches tools, calls them."""
import os
import asyncio
from typing import Any

MCP_URL = os.getenv("MCP_SERVER_URL", "http://194.226.115.120:8001/mcp")

TOOL_LABELS: dict[str, str] = {
    "web_search": "🔍 Ищу в интернете...",
    "get_moex_quote": "📈 Запрашиваю биржу...",
    "get_moex_summary": "📊 Получаю сводку биржи...",
}


async def _get_tools() -> list[dict]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    async with streamablehttp_client(MCP_URL) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.list_tools()
            return [_to_openai_schema(t) for t in result.tools]


async def _call_tool(name: str, args: dict[str, Any]) -> str:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    async with streamablehttp_client(MCP_URL) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool(name, args)
            if result.content:
                return result.content[0].text
            return ""


def _to_openai_schema(tool) -> dict:
    schema = tool.inputSchema or {"type": "object", "properties": {}}
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": schema,
        },
    }


def get_tools_sync() -> list[dict]:
    return asyncio.run(_get_tools())


def call_tool_sync(name: str, args: dict) -> str:
    return asyncio.run(_call_tool(name, args))
