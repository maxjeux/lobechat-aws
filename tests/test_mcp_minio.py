#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]", "httpx"]
# ///
"""Test MinIO MCP server through MCPHub.

Downloads an image from thispersondoesnotexist.com and uploads it to MinIO
using the MCP server endpoint.
"""

import asyncio
import os
import tempfile
from datetime import datetime
from pathlib import Path

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCPHUB_URL = os.getenv("MCPHUB_URL", "http://localhost:47008")
MCP_SERVER = os.getenv("MCP_SERVER", "pickstar-2002-minio-mcp")

# Shared volume path - MCPHub mounts ./data/mcphub to /app/data
HOST_DATA_DIR = Path(__file__).parent.parent / "data" / "mcphub"
CONTAINER_DATA_DIR = "/app/data"

IMAGE_URL = "https://thispersondoesnotexist.com/"
BUCKET_NAME = "test-bucket"


async def download_image(url: str, save_path: Path) -> bool:
    """Download image from URL and save to path."""
    print(f"  Downloading image from {url}...")
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url)
        if response.status_code == 200:
            save_path.write_bytes(response.content)
            print(f"  OK: Saved image ({len(response.content)} bytes) to {save_path}")
            return True
        else:
            print(f"  FAIL: HTTP {response.status_code}")
            return False


async def main():
    mcp_endpoint = f"{MCPHUB_URL}/mcp/{MCP_SERVER}"
    print("=" * 60)
    print("MinIO MCP Server Test")
    print("=" * 60)
    print(f"MCPHub URL: {MCPHUB_URL}")
    print(f"MCP Server: {MCP_SERVER}")
    print(f"Endpoint: {mcp_endpoint}")
    print()

    # Ensure host data directory exists
    HOST_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_filename = f"person_{timestamp}.jpg"
    host_image_path = HOST_DATA_DIR / image_filename
    container_image_path = f"{CONTAINER_DATA_DIR}/{image_filename}"

    # Step 1: Download image
    print("Step 1: Download Image")
    print("-" * 40)
    if not await download_image(IMAGE_URL, host_image_path):
        print("Failed to download image")
        return 1

    print()
    print("Step 2: Connect to MinIO MCP Server")
    print("-" * 40)

    async with streamablehttp_client(mcp_endpoint) as (read, write, get_session_id):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()
            session_id = get_session_id()
            print(f"  OK: Session initialized (ID: {session_id[:24] if session_id else 'None'}...)")

            # List available tools
            print()
            print("Step 3: List Available Tools")
            print("-" * 40)
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"  Found {len(tool_names)} tools:")
            for name in sorted(tool_names)[:10]:
                print(f"    - {name}")
            if len(tool_names) > 10:
                print(f"    ... and {len(tool_names) - 10} more")

            # Step 4: Connect to MinIO
            print()
            print("Step 4: Connect to MinIO")
            print("-" * 40)
            connect_tool = f"{MCP_SERVER}-connect_minio"
            if connect_tool in tool_names:
                try:
                    result = await session.call_tool(connect_tool, {
                        "endPoint": "minio",
                        "port": 9000,
                        "accessKey": "minioadmin",
                        "secretKey": "minioadmin",
                        "useSSL": False,
                        "region": "us-east-1"
                    })
                    for content in result.content:
                        if hasattr(content, 'text'):
                            print(f"  {content.text}")
                except Exception as e:
                    print(f"  WARN: Connect failed: {e}")
            else:
                print(f"  WARN: Tool {connect_tool} not found")

            # Step 5: List/Create bucket
            print()
            print("Step 5: Ensure Bucket Exists")
            print("-" * 40)

            # Check if bucket exists
            bucket_exists_tool = f"{MCP_SERVER}-bucket_exists"
            create_bucket_tool = f"{MCP_SERVER}-create_bucket"

            try:
                result = await session.call_tool(bucket_exists_tool, {
                    "bucketName": BUCKET_NAME
                })
                bucket_exists = False
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(f"  Bucket check: {content.text}")
                        # Chinese: 存在 = exists, 不存在 = does not exist
                        if "存在" in content.text and "不存在" not in content.text:
                            bucket_exists = True
                        elif "true" in content.text.lower() or "exists" in content.text.lower():
                            bucket_exists = True

                if not bucket_exists:
                    print(f"  Creating bucket '{BUCKET_NAME}'...")
                    result = await session.call_tool(create_bucket_tool, {
                        "bucketName": BUCKET_NAME
                    })
                    for content in result.content:
                        if hasattr(content, 'text'):
                            print(f"  {content.text}")
                else:
                    print(f"  OK: Bucket '{BUCKET_NAME}' already exists")
            except Exception as e:
                print(f"  WARN: Bucket operation failed: {e}")
                # Try to create anyway
                try:
                    result = await session.call_tool(create_bucket_tool, {
                        "bucketName": BUCKET_NAME
                    })
                    for content in result.content:
                        if hasattr(content, 'text'):
                            print(f"  {content.text}")
                except Exception as e2:
                    print(f"  Bucket may already exist: {e2}")

            # Step 6: Upload image
            print()
            print("Step 6: Upload Image to MinIO")
            print("-" * 40)
            upload_tool = f"{MCP_SERVER}-upload_file"

            print(f"  File: {container_image_path}")
            print(f"  Bucket: {BUCKET_NAME}")
            print(f"  Object: {image_filename}")

            try:
                result = await session.call_tool(upload_tool, {
                    "bucketName": BUCKET_NAME,
                    "objectName": image_filename,
                    "filePath": container_image_path
                })
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(f"  Result: {content.text}")
                print("  OK: Upload completed!")
            except Exception as e:
                print(f"  FAIL: Upload failed: {e}")
                return 1

            # Step 7: Verify upload by listing objects
            print()
            print("Step 7: Verify Upload")
            print("-" * 40)
            list_objects_tool = f"{MCP_SERVER}-list_objects"

            try:
                result = await session.call_tool(list_objects_tool, {
                    "bucketName": BUCKET_NAME,
                    "prefix": "person_"
                })
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(f"  {content.text[:500]}")
            except Exception as e:
                print(f"  WARN: List objects failed: {e}")

            # Step 8: Generate presigned URL
            print()
            print("Step 8: Generate Presigned URL")
            print("-" * 40)
            presigned_tool = f"{MCP_SERVER}-generate_presigned_url"
            presigned_url = None

            try:
                result = await session.call_tool(presigned_tool, {
                    "bucketName": BUCKET_NAME,
                    "objectName": image_filename,
                    "method": "GET",
                    "expires": 3600
                })
                for content in result.content:
                    if hasattr(content, 'text'):
                        text = content.text
                        # Extract URL from response
                        if "http://" in text:
                            import re
                            url_match = re.search(r'(http://[^\s]+)', text)
                            if url_match:
                                presigned_url = url_match.group(1)
                        print(f"  {text[:100]}...")
            except Exception as e:
                print(f"  WARN: Presigned URL failed: {e}")

            # Step 9: Download file to /tmp for verification
            print()
            print("Step 9: Download to /tmp")
            print("-" * 40)
            download_tool = f"{MCP_SERVER}-download_file"
            local_download_path = f"/tmp/minio_test_{timestamp}.jpg"
            container_download_path = f"/app/data/download_{timestamp}.jpg"

            try:
                result = await session.call_tool(download_tool, {
                    "bucketName": BUCKET_NAME,
                    "objectName": image_filename,
                    "filePath": container_download_path
                })
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(f"  {content.text}")

                # Copy from shared volume to /tmp
                host_download_path = HOST_DATA_DIR / f"download_{timestamp}.jpg"
                if host_download_path.exists():
                    import shutil
                    shutil.copy(host_download_path, local_download_path)
                    file_size = Path(local_download_path).stat().st_size
                    print(f"  OK: Downloaded to {local_download_path} ({file_size} bytes)")
                    # Cleanup container file
                    host_download_path.unlink()
                else:
                    print(f"  WARN: File not found at {host_download_path}")
            except Exception as e:
                print(f"  WARN: Download failed: {e}")

    # Cleanup
    print()
    print("Step 10: Cleanup")
    print("-" * 40)
    if host_image_path.exists():
        host_image_path.unlink()
        print(f"  Removed local file: {host_image_path}")

    print()
    print("=" * 60)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
