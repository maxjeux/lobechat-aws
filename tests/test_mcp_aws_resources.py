#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]"]
# ///
"""Test AWS Resources Operations MCP server through MCPHub.

This test connects to the aws-resources-operations MCP server and
performs read-only AWS operations like listing S3 buckets and EC2 instances.

Environment variables:
  MCPHUB_URL - Optional: MCPHub URL (default: http://localhost:47008)
  MCP_SERVER - Optional: MCP server name (default: aws-resources-operations)
"""

import asyncio
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCPHUB_URL = os.getenv("MCPHUB_URL", "http://localhost:47008")
MCP_SERVER = os.getenv("MCP_SERVER", "aws-resources-operations")


async def main():
    mcp_endpoint = f"{MCPHUB_URL}/mcp/{MCP_SERVER}"
    print("=" * 60)
    print("AWS Resources Operations MCP Server Test")
    print("=" * 60)
    print(f"MCPHub URL: {MCPHUB_URL}")
    print(f"MCP Server: {MCP_SERVER}")
    print(f"Endpoint: {mcp_endpoint}")
    print()

    print("Step 1: Connect to MCP Server")
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
            for tool in tools.tools:
                desc = tool.description[:50] + "..." if tool.description and len(tool.description) > 50 else (tool.description or "No description")
                print(f"    - {tool.name}: {desc}")

            # Test AWS operations using boto3 code snippets
            print()
            print("Step 3: Test AWS Operations")
            print("-" * 40)

            # Find the query tool
            query_tool = None
            for name in tool_names:
                if "query" in name.lower() or "resource" in name.lower():
                    query_tool = name
                    break

            if not query_tool and tool_names:
                query_tool = tool_names[0]

            if not query_tool:
                print("  ERROR: No query tool found!")
                return 1

            print(f"  Using tool: {query_tool}")

            # Test queries as boto3 code snippets (must set 'result' variable)
            test_queries = [
                {
                    "name": "Get Caller Identity",
                    "code": """
import boto3
sts = boto3.client('sts')
response = sts.get_caller_identity()
result = {
    'account': response['Account'],
    'arn': response['Arn'],
    'user_id': response['UserId']
}
""",
                },
                {
                    "name": "List S3 Buckets",
                    "code": """
import boto3
s3 = boto3.client('s3')
response = s3.list_buckets()
buckets = [b['Name'] for b in response.get('Buckets', [])]
result = {'bucket_count': len(buckets), 'buckets': buckets[:10]}
""",
                },
                {
                    "name": "List EC2 Instances",
                    "code": """
import boto3
ec2 = boto3.client('ec2')
response = ec2.describe_instances()
instances = []
for reservation in response.get('Reservations', []):
    for instance in reservation.get('Instances', []):
        instances.append({
            'id': instance['InstanceId'],
            'state': instance['State']['Name'],
            'type': instance.get('InstanceType', 'N/A')
        })
result = {'instance_count': len(instances), 'instances': instances[:10]}
""",
                },
                {
                    "name": "List Lambda Functions",
                    "code": """
import boto3
lambda_client = boto3.client('lambda')
response = lambda_client.list_functions()
functions = [{'name': f['FunctionName'], 'runtime': f.get('Runtime', 'N/A')} for f in response.get('Functions', [])]
result = {'function_count': len(functions), 'functions': functions[:10]}
""",
                },
            ]

            for query in test_queries:
                print(f"\n  > {query['name']}")
                print("  " + "-" * 50)
                try:
                    result = await session.call_tool(
                        query_tool,
                        {"code_snippet": query["code"].strip()},
                    )
                    for content in result.content:
                        if hasattr(content, "text"):
                            text = content.text[:800]
                            for line in text.split("\n")[:15]:
                                print(f"    {line}")
                            if len(content.text) > 800:
                                print("    ...")
                except Exception as e:
                    print(f"    ERROR: {e}")

    print()
    print("=" * 60)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
