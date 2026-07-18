"""Day 34: local file-agent tools + human-in-the-loop confirmation.

Separate from `mcp_client.py` (days 31/33) — these tools run in-process, not
over MCP, since they need the sandbox/danger/confirm machinery wired directly
into chat.py's tool-calling loop. Importing this package registers the
built-in fs tools (see `fs_tools.py`) as a side effect, same pattern as
`commands_help`/`commands_support` registering slash commands.
"""
from agent_web.services.tools import fs_tools  # noqa: F401 — registers read_file/search_files/list_dir/write_file/delete_file
