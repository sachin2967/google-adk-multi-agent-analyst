"""Exercise the real MCP JSON-RPC lifecycle over local stdio."""

import asyncio

from mcp import ClientSession
from mcp.client.stdio import stdio_client

from src.agents.adk_system import _mcp_server_parameters


def test_stdio_server_lists_and_executes_read_only_tools():
    parameters = _mcp_server_parameters()

    async def exercise_protocol():
        async with (
            stdio_client(parameters) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            tools = await session.list_tools()
            names = {tool.name for tool in tools.tools}
            assert names == {"get_analytics_schema", "analyze_commerce"}
            analyze_schema = next(
                tool.inputSchema
                for tool in tools.tools
                if tool.name == "analyze_commerce"
            )
            assert analyze_schema["properties"]["metric"]["enum"] == [
                "revenue",
                "orders",
                "average_review",
                "average_delivery_days",
            ]

            result = await session.call_tool(
                "analyze_commerce",
                arguments={"metric": "revenue", "group_by": "category", "limit": 5},
            )
            assert not result.isError
            assert result.structuredContent["row_count"] > 0
            assert len(result.structuredContent["records"]) <= 5

            rejected = await session.call_tool(
                "analyze_commerce",
                arguments={"metric": "revenue; DROP TABLE orders"},
            )
            assert rejected.isError

    asyncio.run(exercise_protocol())
