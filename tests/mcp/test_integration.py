"""End-to-end loopback: phronesis client adapter against phronesis server."""

from __future__ import annotations

from mcp.shared.memory import create_connected_server_and_client_session

from phronesis.mcp.client import McpClient
from phronesis.mcp.ids import mcp_client_id_generator
from phronesis.mcp.server import mcp_server
from phronesis.mcp.server_spec import McpServerSpec
from phronesis.mcp.transport import StdioTransport
from phronesis.tools import tool


@tool
def add(a: int, b: int) -> int:
    """Sum two integers."""
    return a + b


@tool
def upper(text: str) -> str:
    """Uppercase text."""
    return text.upper()


class TestLoopback:
    async def test_phronesis_client_calls_phronesis_server(self) -> None:
        server = mcp_server(name="math", tools=(add, upper))
        spec = McpServerSpec(
            name="math",
            transport=StdioTransport(command="python"),
        )
        lowlevel = server._build_lowlevel_server()

        async with create_connected_server_and_client_session(lowlevel) as session:
            client = McpClient(
                spec=spec,
                session=session,
                client_id=mcp_client_id_generator.from_canonical("phronesis.mcp.clients.math"),
            )

            tools = await client.list_tools()
            by_name = {str(t.spec.name): t for t in tools}

            add_result = await by_name["add"].invoke({"a": 7, "b": 8})
            upper_result = await by_name["upper"].invoke({"text": "hi"})

        assert add_result == "15"
        assert upper_result == "HI"

    async def test_remote_schema_round_trips(self) -> None:
        server = mcp_server(name="math", tools=(add,))
        spec = McpServerSpec(
            name="math",
            transport=StdioTransport(command="python"),
        )
        lowlevel = server._build_lowlevel_server()

        async with create_connected_server_and_client_session(lowlevel) as session:
            client = McpClient(
                spec=spec,
                session=session,
                client_id=mcp_client_id_generator.from_canonical("phronesis.mcp.clients.math"),
            )

            tools = await client.list_tools()

        adapted_schema = tools[0].get_schema()
        local_schema = add.get_schema()

        assert adapted_schema == local_schema
