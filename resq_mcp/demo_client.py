"""Small real MCP client for demonstrating the ResQ-AI Alexa+ track server.

Run the server in one terminal, then run this module in another. It performs
MCP initialization, lists tools, and calls one read-only tool over Streamable HTTP.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


def _arguments(args: argparse.Namespace) -> dict[str, Any]:
    if args.tool == "list_incidents":
        return {"status": args.status, "limit": args.limit}
    if args.tool in {"get_incident_details", "explain_priority"}:
        return {"incident_id": args.incident_id}
    if args.tool == "find_shelters":
        return {"minimum_spaces": args.minimum_spaces}
    return {}


async def run_demo(args: argparse.Namespace) -> int:
    try:
        async with streamablehttp_client(args.url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                initialized = await session.initialize()
                tools_result = await session.list_tools()
                tool_names = [tool.name for tool in tools_result.tools]
                print(f"Connected to MCP server: {initialized.serverInfo.name}")
                print(f"Negotiated MCP protocol version: {initialized.protocolVersion}")
                print("Discovered tools:", ", ".join(tool_names))

                if args.tool not in tool_names:
                    print(f"Requested tool is not available: {args.tool}")
                    return 2

                result = await session.call_tool(args.tool, _arguments(args))
                print(f"\nTool result: {args.tool}")
                for item in result.content:
                    if getattr(item, "text", None):
                        try:
                            print(json.dumps(json.loads(item.text), indent=2, ensure_ascii=False))
                        except json.JSONDecodeError:
                            print(item.text)
                if result.isError:
                    print("The MCP server reported a tool error.")
                    return 1
                return 0
    except Exception as exc:
        print(f"Could not connect to the MCP server at {args.url}: {exc}")
        print("Start it first with: python -m resq_mcp.server")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Demo the ResQ-AI MCP server using a real MCP client.")
    parser.add_argument("--url", default="http://127.0.0.1:8000/mcp", help="Streamable HTTP MCP endpoint")
    parser.add_argument(
        "--tool",
        default="list_incidents",
        choices=(
            "list_incidents", "get_incident_details", "explain_priority",
            "get_resource_status", "find_shelters", "generate_incident_brief",
            "get_live_government_alerts",
        ),
        help="Read-only MCP tool to invoke",
    )
    parser.add_argument("--status", default="active", help="Incident status for list_incidents")
    parser.add_argument("--limit", type=int, default=5, help="Maximum incidents for list_incidents")
    parser.add_argument("--incident-id", default="INC-001", help="Incident ID for detail/priority tools")
    parser.add_argument("--minimum-spaces", type=int, default=0, help="Minimum shelter spaces for find_shelters")
    return asyncio.run(run_demo(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
