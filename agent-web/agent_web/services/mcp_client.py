"""MCP client — connects to MULTIPLE remote MCP servers, merges tools, routes calls."""
import os
import asyncio
import concurrent.futures
from typing import Any

# Registry: server_name → URL
MCP_SERVERS: dict[str, str] = {
    "finance": os.getenv("MCP_SERVER_URL", "http://194.226.115.120:8001/mcp"),
    "github":  os.getenv("MCP_GITHUB_URL", "http://194.226.115.120:8003/mcp"),
}

# tool_name → server_name (populated on first get_tools_sync call)
_tool_registry: dict[str, str] = {}

TOOL_LABELS: dict[str, str] = {
    # Finance / Crypto (VPS)
    "get_current_datetime":  "🕐 Узнаю текущее время...",
    "web_search":            "🔍 Ищу в интернете...",
    "get_moex_quote":        "📈 Запрашиваю биржу...",
    "get_moex_summary":      "📊 Получаю сводку биржи...",
    "get_moex_index":        "📊 Запрашиваю индекс MOEX...",
    "get_moex_history":      "📈 Достаю историю из БД...",
    "get_crypto_klines":     "📊 Загружаю свечи Binance...",
    "calculate_indicators":  "🧮 Считаю RSI/MACD...",
    "save_report":           "💾 Сохраняю отчёт...",
    # GitHub
    "create_issue":          "🐙 Создаю GitHub Issue...",
    "get_issue":             "🐙 Читаю GitHub Issue...",
    "list_issues":           "🐙 Получаю список Issues...",
    "search_repositories":   "🔍 Ищу репозитории GitHub...",
    "get_file_contents":     "📄 Читаю файл из GitHub...",
    "push_files":            "📤 Отправляю файлы в GitHub...",
}


async def _get_tools_from_server(server_name: str, server_url: str) -> list[dict]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    async with streamablehttp_client(server_url) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.list_tools()
            tools = [_to_openai_schema(t) for t in result.tools]
            for t in tools:
                _tool_registry[t["function"]["name"]] = server_name
            return tools


async def _get_all_tools() -> list[dict]:
    global _tool_registry
    _tool_registry = {}
    all_tools: list[dict] = []
    for server_name, server_url in MCP_SERVERS.items():
        try:
            tools = await _get_tools_from_server(server_name, server_url)
            all_tools.extend(tools)
        except Exception as e:
            print(f"[mcp_client] Server '{server_name}' ({server_url}) unavailable: {e}")
    return all_tools


async def _call_tool_on_server(server_url: str, name: str, args: dict[str, Any]) -> str:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    async with streamablehttp_client(server_url) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool(name, args)
            if result.content:
                return result.content[0].text
            return ""


async def _call_tool(name: str, args: dict[str, Any]) -> str:
    server_name = _tool_registry.get(name, "finance")
    server_url = MCP_SERVERS.get(server_name, MCP_SERVERS["finance"])
    return await _call_tool_on_server(server_url, name, args)


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


def _run_in_new_loop(coro):
    """Run async coroutine in a fresh thread+loop — safe inside async FastAPI context."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result(timeout=30)


def get_tools_sync() -> list[dict]:
    return _run_in_new_loop(_get_all_tools())


def call_tool_sync(name: str, args: dict) -> str:
    return _run_in_new_loop(_call_tool(name, args))
