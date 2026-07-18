"""MCP client — connects to MULTIPLE remote MCP servers, merges tools, routes calls."""
import os
import asyncio
import concurrent.futures
from pathlib import Path
from typing import Any

# Load .env from agent-web directory (if present) — before any os.getenv calls
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass

# Registry: server_name → URL
MCP_SERVERS: dict[str, str] = {
    "finance": os.getenv("MCP_SERVER_URL", "http://194.226.115.120:8001/mcp"),
    "github":  os.getenv("MCP_GITHUB_URL", "http://194.226.115.120:8003/mcp"),
    # Day 31: local project server (git/fs facts) — runs on THIS machine, not the VPS,
    # since the VPS can't see the working copy. Degrades gracefully if not running
    # (same try/except-per-server pattern as finance/github below).
    "project": os.getenv("MCP_PROJECT_URL", "http://127.0.0.1:8002/mcp"),
}

# Extra headers per server (e.g. GitHub OAuth token)
_GITHUB_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")
MCP_SERVER_HEADERS: dict[str, dict[str, str]] = {
    "github": {"Authorization": f"Bearer {_GITHUB_TOKEN}"} if _GITHUB_TOKEN else {},
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
    "issue_write":           "🐙 Создаю/обновляю GitHub Issue...",
    "issue_read":            "🐙 Читаю GitHub Issue...",
    "list_issues":           "🐙 Получаю список Issues...",
    # Project (local)
    "git_current_branch":    "🌿 Узнаю текущую ветку...",
    "git_status":            "🌿 Смотрю git status...",
    "git_diff":               "🌿 Смотрю git diff...",
    "list_project_files":    "📁 Ищу файлы проекта...",
    # Support tickets (day 33, local)
    "list_tickets":          "🎫 Смотрю список тикетов...",
    "get_ticket":            "🎫 Читаю тикет...",
}


def _mcp_http_client_factory(headers=None, timeout=None, auth=None):
    """Same defaults as mcp's create_mcp_http_client, but trust_env=False —
    on Windows with a system SOCKS proxy configured (VPN software), httpx
    otherwise tries to route this VPS call through it and fails with
    "Unknown scheme for proxy URL socks4://...", even though the VPS is
    directly reachable without any proxy."""
    import httpx
    from mcp.shared._httpx_utils import MCP_DEFAULT_SSE_READ_TIMEOUT, MCP_DEFAULT_TIMEOUT

    kwargs: dict = {"follow_redirects": True, "trust_env": False}
    kwargs["timeout"] = timeout if timeout is not None else httpx.Timeout(
        MCP_DEFAULT_TIMEOUT, read=MCP_DEFAULT_SSE_READ_TIMEOUT
    )
    if headers is not None:
        kwargs["headers"] = headers
    if auth is not None:
        kwargs["auth"] = auth
    return httpx.AsyncClient(**kwargs)


async def _get_tools_from_server(server_name: str, server_url: str) -> list[dict]:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    headers = MCP_SERVER_HEADERS.get(server_name, {})
    async with streamablehttp_client(
        server_url, headers=headers, httpx_client_factory=_mcp_http_client_factory
    ) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.list_tools()
            available = {t.name for t in result.tools}
            if server_name == "github":
                # Use simplified Gemini-compatible schemas for GitHub tools
                tools = _github_simple_tools(available)
            else:
                tools = [_to_openai_schema(t) for t in result.tools]
            for t in tools:
                _tool_registry[t["function"]["name"]] = server_name
            return tools


async def _get_all_tools() -> list[dict]:
    _tool_registry.clear()
    all_tools: list[dict] = []
    for server_name, server_url in MCP_SERVERS.items():
        try:
            tools = await _get_tools_from_server(server_name, server_url)
            all_tools.extend(tools)
        except Exception as e:
            print(f"[mcp_client] Server '{server_name}' ({server_url}) unavailable: {e}")
    return all_tools


async def _call_tool_on_server(server_name: str, server_url: str, name: str, args: dict[str, Any]) -> str:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    headers = MCP_SERVER_HEADERS.get(server_name, {})
    async with streamablehttp_client(
        server_url, headers=headers, httpx_client_factory=_mcp_http_client_factory
    ) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()
            result = await session.call_tool(name, args)
            if result.content:
                return result.content[0].text
            return ""


async def _call_tool(name: str, args: dict[str, Any]) -> str:
    server_name = _tool_registry.get(name, "finance")
    server_url = MCP_SERVERS.get(server_name, MCP_SERVERS["finance"])
    return await _call_tool_on_server(server_name, server_url, name, args)


_GITHUB_SIMPLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "issue_write",
            "description": "Create a new issue (method=create) or update existing (method=update) in a GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "description": "Operation: 'create' to open new issue, 'update' to edit existing", "enum": ["create", "update"]},
                    "owner": {"type": "string", "description": "Repository owner (username or org)"},
                    "repo":  {"type": "string", "description": "Repository name"},
                    "title": {"type": "string", "description": "Issue title (required for create)"},
                    "body":  {"type": "string", "description": "Issue body/description (markdown)"},
                    "issue_number": {"type": "integer", "description": "Issue number to update (required for update)"},
                    "state": {"type": "string", "description": "Issue state: open or closed", "enum": ["open", "closed"]},
                },
                "required": ["method", "owner", "repo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_issues",
            "description": "List issues in a GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner"},
                    "repo":  {"type": "string", "description": "Repository name"},
                    "state": {"type": "string", "description": "Filter by state: open, closed, or all"},
                    "limit": {"type": "integer", "description": "Max number of issues to return"},
                },
                "required": ["owner", "repo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "issue_read",
            "description": "Get details of a specific issue in a GitHub repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "owner":        {"type": "string",  "description": "Repository owner"},
                    "repo":         {"type": "string",  "description": "Repository name"},
                    "issue_number": {"type": "integer", "description": "Issue number"},
                },
                "required": ["owner", "repo", "issue_number"],
            },
        },
    },
]


def _github_simple_tools(available: set[str]) -> list[dict]:
    """Return simplified Gemini-compatible schemas for GitHub tools that exist on server."""
    return [t for t in _GITHUB_SIMPLE_TOOLS if t["function"]["name"] in available]


def _sanitize_schema(obj: Any) -> Any:
    """Remove boolean/null values from enum arrays — Gemini requires string-only enums."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == "enum" and isinstance(v, list):
                # Keep only string values; if nothing left, drop the field
                strings = [x for x in v if isinstance(x, str)]
                if strings:
                    result[k] = strings
            else:
                result[k] = _sanitize_schema(v)
        return result
    if isinstance(obj, list):
        return [_sanitize_schema(x) for x in obj]
    return obj


def _to_openai_schema(tool) -> dict:
    schema = tool.inputSchema or {"type": "object", "properties": {}}
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": _sanitize_schema(schema),
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
