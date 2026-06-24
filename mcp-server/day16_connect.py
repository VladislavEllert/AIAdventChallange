"""Day 16 demo: connect to MCP server, list available tools."""
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_URL = "http://194.226.115.120:8001/mcp"


async def main():
    print(f"Connecting to MCP server: {MCP_URL}")
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"\nAvailable tools ({len(tools.tools)}):")
            for t in tools.tools:
                print(f"  • {t.name}: {t.description[:80]}")
    print("\nDone.")


asyncio.run(main())
