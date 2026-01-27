#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]"]
# ///
"""Test Playwright MCP server through MCPHub.

Takes a screenshot of oriolrius.me using the Playwright browser.
"""

import asyncio
import os
import base64
from datetime import datetime
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCPHUB_URL = os.getenv("MCPHUB_URL", "http://localhost:47008")
MCP_SERVER = os.getenv("MCP_SERVER", "playwright")

TARGET_URL = "https://oriolrius.me"
OUTPUT_DIR = Path("/tmp")


async def main():
    mcp_endpoint = f"{MCPHUB_URL}/mcp/{MCP_SERVER}"
    print("=" * 60)
    print("Playwright MCP Server Test")
    print("=" * 60)
    print(f"MCPHub URL: {MCPHUB_URL}")
    print(f"MCP Server: {MCP_SERVER}")
    print(f"Endpoint: {mcp_endpoint}")
    print(f"Target URL: {TARGET_URL}")
    print()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_filename = f"screenshot_{timestamp}.png"
    screenshot_path = OUTPUT_DIR / screenshot_filename

    print("Step 1: Connect to Playwright MCP Server")
    print("-" * 40)

    async with streamablehttp_client(mcp_endpoint) as (read, write, get_session_id):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()
            session_id = get_session_id()
            print(f"  OK: Session initialized (ID: {session_id[:24] if session_id else 'None'}...)")

            # List available tools
            print()
            print("Step 2: List Available Tools")
            print("-" * 40)
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"  Found {len(tool_names)} tools:")
            for name in sorted(tool_names):
                print(f"    - {name}")

            # Step 3: Navigate to URL
            print()
            print("Step 3: Navigate to URL")
            print("-" * 40)
            navigate_tool = "playwright-browser_navigate"

            if navigate_tool not in tool_names:
                # Try alternative naming
                navigate_tool = next((t for t in tool_names if "navigate" in t.lower() and "back" not in t.lower()), None)

            if navigate_tool:
                print(f"  Using tool: {navigate_tool}")
                print(f"  Navigating to {TARGET_URL}...")
                try:
                    result = await session.call_tool(navigate_tool, {
                        "url": TARGET_URL
                    })
                    for content in result.content:
                        if hasattr(content, 'text'):
                            # Truncate long output
                            text = content.text
                            if len(text) > 500:
                                text = text[:500] + "..."
                            print(f"  {text}")
                except Exception as e:
                    print(f"  ERROR: Navigation failed: {e}")
                    return 1
            else:
                print(f"  ERROR: Navigate tool not found")
                return 1

            # Resize browser to 1920x1080
            print()
            print("Step 4: Resize Browser to 1920x1080")
            print("-" * 40)
            resize_tool = "playwright-browser_resize"

            if resize_tool in tool_names:
                try:
                    result = await session.call_tool(resize_tool, {
                        "width": 1920,
                        "height": 1080
                    })
                    for content in result.content:
                        if hasattr(content, 'text'):
                            print(f"  {content.text[:200]}")
                except Exception as e:
                    print(f"  WARN: Resize failed: {e}")
            else:
                print(f"  WARN: Resize tool not found")

            # Wait for page to load
            print()
            print("Step 5: Wait for Page Load")
            print("-" * 40)
            await asyncio.sleep(2)
            print("  OK: Waited 2 seconds for page to load")

            # Step 6: Take screenshot
            print()
            print("Step 6: Take Screenshot")
            print("-" * 40)
            screenshot_tool = "playwright-browser_take_screenshot"

            if screenshot_tool not in tool_names:
                screenshot_tool = next((t for t in tool_names if "screenshot" in t.lower()), None)

            container_screenshot_path = None
            if screenshot_tool:
                print(f"  Using tool: {screenshot_tool}")
                print(f"  Taking screenshot...")
                try:
                    result = await session.call_tool(screenshot_tool, {})

                    screenshot_saved = False
                    for content in result.content:
                        if hasattr(content, 'text'):
                            text = content.text
                            # Extract container path from response
                            import re
                            match = re.search(r'\.\./tmp/playwright-mcp-output/(\d+/[^)]+\.png)', text)
                            if match:
                                container_screenshot_path = f"/tmp/playwright-mcp-output/{match.group(1)}"
                            if len(text) > 200:
                                text = text[:200] + "..."
                            print(f"  Response: {text}")

                    if container_screenshot_path:
                        # Copy full-resolution screenshot from container using docker cp
                        import subprocess
                        print(f"  Copying full-res screenshot from container: {container_screenshot_path}")
                        cp_result = subprocess.run(
                            ["docker", "cp", f"mcphub:{container_screenshot_path}", str(screenshot_path)],
                            capture_output=True, text=True
                        )
                        if cp_result.returncode == 0 and screenshot_path.exists():
                            print(f"  OK: Screenshot copied to {screenshot_path}")
                            print(f"  Size: {screenshot_path.stat().st_size} bytes")
                            screenshot_saved = True
                        else:
                            print(f"  WARN: Failed to copy: {cp_result.stderr}")

                    if not screenshot_saved:
                        print("  WARN: No screenshot saved")

                except Exception as e:
                    print(f"  ERROR: Screenshot failed: {e}")
                    return 1
            else:
                print(f"  ERROR: Screenshot tool not found")
                return 1

            # Step 6: Get page snapshot (accessibility tree)
            print()
            print("Step 7: Get Page Snapshot")
            print("-" * 40)
            snapshot_tool = "playwright-browser_snapshot"

            if snapshot_tool not in tool_names:
                snapshot_tool = next((t for t in tool_names if "snapshot" in t.lower()), None)

            if snapshot_tool:
                print(f"  Using tool: {snapshot_tool}")
                try:
                    result = await session.call_tool(snapshot_tool, {})
                    for content in result.content:
                        if hasattr(content, 'text'):
                            text = content.text
                            # Show first 500 chars of snapshot
                            lines = text.split('\n')[:15]
                            print("  Page structure (first 15 lines):")
                            for line in lines:
                                print(f"    {line[:80]}")
                            if len(text.split('\n')) > 15:
                                print(f"    ... ({len(text.split(chr(10)))} total lines)")
                except Exception as e:
                    print(f"  WARN: Snapshot failed: {e}")

            # Step 7: Close browser
            print()
            print("Step 8: Close Browser")
            print("-" * 40)
            close_tool = "playwright-browser_close"

            if close_tool not in tool_names:
                close_tool = next((t for t in tool_names if "close" in t.lower()), None)

            if close_tool:
                try:
                    result = await session.call_tool(close_tool, {})
                    print("  OK: Browser closed")
                except Exception as e:
                    print(f"  WARN: Close failed (may already be closed): {e}")

    # Verify screenshot
    print()
    print("Step 9: Verify Screenshot")
    print("-" * 40)
    if screenshot_path.exists():
        size = screenshot_path.stat().st_size
        print(f"  File: {screenshot_path}")
        print(f"  Size: {size} bytes")

        # Check if it's a valid PNG
        with open(screenshot_path, 'rb') as f:
            header = f.read(8)
            if header[:4] == b'\x89PNG':
                print("  Format: PNG (valid)")
            else:
                print(f"  Format: Unknown (header: {header[:4]})")

        print(f"  OK: Screenshot saved successfully!")
    else:
        print(f"  ERROR: Screenshot file not found at {screenshot_path}")
        return 1

    print()
    print("=" * 60)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print(f"\nScreenshot available at: {screenshot_path}")
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
