"""Tests for :class:`McpClient` against the in-memory loopback."""

from __future__ import annotations

import pytest

from phronesis.mcp.client import _client_id_for, _transport_kind
from phronesis.mcp.ids import McpClientId
from phronesis.mcp.server import mcp_server
from phronesis.mcp.server_spec import McpServerSpec
from phronesis.mcp.transport import HttpTransport, StdioTransport
from phronesis.tools import tool
from phronesis.tools.tool import Tool


@tool
def adder(a: int, b: int) -> int:
    """Sum two integers."""
    return a + b


@tool
def greeter(name: str) -> str:
    """Greet the caller."""
    return f"hello {name}"


class TestHelpers:
    def test_client_id_for_derives_from_server_id(self) -> None:
        spec = McpServerSpec(
            name="math",
            transport=StdioTransport(command="python"),
        )

        client_id = _client_id_for(spec)

        assert isinstance(client_id, McpClientId)
        assert client_id.canonical == "phronesis.mcp.clients.math"

    def test_transport_kind_stdio(self) -> None:
        assert _transport_kind(StdioTransport(command="python")) == "stdio"

    def test_transport_kind_http(self) -> None:
        assert _transport_kind(HttpTransport(url="https://x")) == "http"


class TestListToolsLoopback:
    async def test_lists_remote_tools_as_phronesis_tools(self, make_connected_client) -> None:
        server = mcp_server(name="math", tools=(adder, greeter))
        spec = McpServerSpec(
            name="math",
            transport=StdioTransport(command="python"),
        )

        async with make_connected_client(server, spec) as client:
            tools = await client.list_tools()

        assert len(tools) == 2
        names = {str(t.spec.name) for t in tools}

        assert names == {"adder", "greeter"}

    async def test_adapted_tool_invocation_round_trips(
        self,
        make_connected_client,
    ) -> None:
        server = mcp_server(name="math", tools=(adder,))
        spec = McpServerSpec(
            name="math",
            transport=StdioTransport(command="python"),
        )

        async with make_connected_client(server, spec) as client:
            tools = await client.list_tools()
            adapted = next(t for t in tools if str(t.spec.name) == "adder")

            result = await adapted.invoke({"a": 2, "b": 3})

        assert result == "5"

    async def test_adapted_tools_carry_remote_schema(
        self,
        make_connected_client,
    ) -> None:
        server = mcp_server(name="math", tools=(adder,))
        spec = McpServerSpec(
            name="math",
            transport=StdioTransport(command="python"),
        )

        async with make_connected_client(server, spec) as client:
            tools = await client.list_tools()

        schema = tools[0].get_schema()

        assert schema["type"] == "object"
        assert set(schema["properties"]) == {"a", "b"}


class TestClientIdentity:
    async def test_exposes_server_and_client_ids(self, make_connected_client) -> None:
        server = mcp_server(name="math", tools=(adder,))
        spec = McpServerSpec(
            name="math",
            transport=StdioTransport(command="python"),
        )

        async with make_connected_client(server, spec) as client:
            assert client.server_id is spec.server_id
            assert client.client_id.canonical == "phronesis.mcp.clients.math"


class TestEmptyServer:
    async def test_empty_tool_list(self, make_connected_client) -> None:
        server = mcp_server(name="empty", tools=())
        spec = McpServerSpec(
            name="empty",
            transport=StdioTransport(command="python"),
        )

        async with make_connected_client(server, spec) as client:
            tools = await client.list_tools()

        assert tools == ()


class TestPlaceholder:
    def test_tool_type_imported(self) -> None:
        assert Tool is not None


# Suppress unused-import warning for pytest.
_ = pytest
