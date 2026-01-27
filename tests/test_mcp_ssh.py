#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]", "httpx"]
# ///
"""Test MCP SSH connection through MCPHub."""

import asyncio
import os
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCPHUB_URL = os.getenv("MCPHUB_URL", "http://localhost:47008")
MCP_SERVER = os.getenv("MCP_SERVER", "ssh-exec")


async def main():
    mcp_endpoint = f"{MCPHUB_URL}/mcp/{MCP_SERVER}"
    print(f"Connecting to: {mcp_endpoint}")

    async with streamablehttp_client(mcp_endpoint) as (read, write, get_session_id):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()
            session_id = get_session_id()
            print(f"Session initialized (ID: {session_id})")

            # List available tools
            print("\n=== Available Tools ===")
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description[:60] if tool.description else 'No description'}...")

            # Execute SSH commands
            print("\n=== Testing SSH Commands ===")

            # Test whoami
            print("\n> whoami")
            result = await session.call_tool("ssh-exec-ssh_exec", {"command": "whoami"})
            for content in result.content:
                if hasattr(content, 'text'):
                    print(content.text)

            # Test uptime
            print("\n> uptime")
            result = await session.call_tool("ssh-exec-ssh_exec", {"command": "uptime"})
            for content in result.content:
                if hasattr(content, 'text'):
                    print(content.text)

            # Test ls
            print("\n> ls -la /home/oriol")
            result = await session.call_tool("ssh-exec-ssh_exec", {"command": "ls", "arguments": "-la /home/oriol"})
            for content in result.content:
                if hasattr(content, 'text'):
                    print(content.text)


if __name__ == "__main__":
    asyncio.run(main())
