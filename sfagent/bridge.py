"""MCP bridge: connect to a school-finance MCP server and expose its tools
in the shape the Anthropic Messages API expects.

Supports the deployed streamable HTTP server (default) or a locally spawned
stdio server. The agent layer never knows which one it is talking to.
"""

from __future__ import annotations

import json
import sys
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

try:
    from mcp.client.streamable_http import streamable_http_client
except ImportError:  # SDK versions before the rename
    from mcp.client.streamable_http import (
        streamablehttp_client as streamable_http_client,
    )

DEFAULT_URL = "https://school-finance-mcp.onrender.com/mcp"
# sys.executable, not "python": the spawned server must live in the same
# environment (and venv) as the agent, or --stdio breaks on machines where
# "python" is missing or points elsewhere.
STDIO_COMMAND = [sys.executable, "-m", "school_finance_mcp"]


@asynccontextmanager
async def open_mcp(url: str | None = None, *, stdio: bool = False):
    """Yield an initialized ClientSession for the chosen transport."""
    if stdio:
        params = StdioServerParameters(command=STDIO_COMMAND[0], args=STDIO_COMMAND[1:])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    else:
        async with streamable_http_client(url or DEFAULT_URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session


async def list_anthropic_tools(session: ClientSession) -> list[dict]:
    """MCP tool schemas, converted verbatim to Anthropic tool definitions."""
    listed = await session.list_tools()
    return [
        {
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": tool.inputSchema,
        }
        for tool in listed.tools
    ]


async def call_mcp_tool(session: ClientSession, name: str, arguments: dict) -> str:
    """Execute one MCP tool call and return its text payload."""
    result = await session.call_tool(name, arguments)
    parts = [block.text for block in result.content if getattr(block, "text", None)]
    text = "\n".join(parts) if parts else json.dumps({"error": "empty tool result"})
    if result.isError:
        return json.dumps({"error": text})
    return text
