"""Tests for :class:`PhronesisMcpServer` and the :func:`mcp_server` factory."""

from __future__ import annotations

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from phronesis.mcp.ids import McpServerId
from phronesis.mcp.server import PhronesisMcpServer, mcp_server
from phronesis.tools import tool


@tool
def echo(message: str) -> str:
    """Return the message as-is."""
    return message


@tool
async def add_async(a: int, b: int) -> int:
    """Sum two integers asynchronously."""
    return a + b


@tool
def crash() -> str:
    """Always raise."""
    raise ValueError("nope")


class TestFactory:
    def test_returns_phronesis_mcp_server(self) -> None:
        server = mcp_server(name="x", tools=(echo,))

        assert isinstance(server, PhronesisMcpServer)

    def test_defaults_server_id_from_name(self) -> None:
        server = mcp_server(name="math", tools=(echo,))

        assert server.server_id.canonical == "phronesis.mcp.servers.math"

    def test_accepts_explicit_server_id(self) -> None:
        custom = McpServerId("custom.foo.bar")
        server = mcp_server(name="x", tools=(echo,), server_id=custom)

        assert server.server_id is custom

    def test_accepts_iterable_of_tools(self) -> None:
        server = mcp_server(name="x", tools=iter([echo]))

        assert server.tools == (echo,)


class TestDuplicates:
    def test_duplicate_names_raise(self) -> None:
        with pytest.raises(ValueError):
            mcp_server(name="x", tools=(echo, echo))


class TestListToolsLoopback:
    async def test_publishes_every_tool(self) -> None:
        server = mcp_server(name="x", tools=(echo, add_async))
        lowlevel = server._build_lowlevel_server()

        async with create_connected_server_and_client_session(lowlevel) as session:
            await session.initialize()
            result = await session.list_tools()

        names = {t.name for t in result.tools}

        assert names == {"echo", "add_async"}


class TestCallToolLoopback:
    async def test_sync_tool_round_trip(self) -> None:
        server = mcp_server(name="x", tools=(echo,))
        lowlevel = server._build_lowlevel_server()

        async with create_connected_server_and_client_session(lowlevel) as session:
            await session.initialize()
            result = await session.call_tool(name="echo", arguments={"message": "hi"})

        assert result.isError is False
        assert result.content[0].text == "hi"  # type: ignore[union-attr]

    async def test_async_tool_round_trip(self) -> None:
        server = mcp_server(name="x", tools=(add_async,))
        lowlevel = server._build_lowlevel_server()

        async with create_connected_server_and_client_session(lowlevel) as session:
            await session.initialize()
            result = await session.call_tool(name="add_async", arguments={"a": 1, "b": 2})

        assert result.isError is False
        assert result.content[0].text == "3"  # type: ignore[union-attr]

    async def test_unknown_tool_returns_error(self) -> None:
        server = mcp_server(name="x", tools=(echo,))
        lowlevel = server._build_lowlevel_server()

        async with create_connected_server_and_client_session(lowlevel) as session:
            await session.initialize()
            result = await session.call_tool(name="missing", arguments={})

        assert result.isError is True

    async def test_tool_error_returns_error_result(self) -> None:
        server = mcp_server(name="x", tools=(crash,))
        lowlevel = server._build_lowlevel_server()

        async with create_connected_server_and_client_session(lowlevel) as session:
            await session.initialize()
            result = await session.call_tool(name="crash", arguments={})

        assert result.isError is True
