"""Shared fixtures for the :mod:`phronesis.mcp` tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest
from mcp import ClientSession
from mcp.shared.memory import create_connected_server_and_client_session

from phronesis.mcp.client import McpClient
from phronesis.mcp.ids import mcp_client_id_generator
from phronesis.mcp.server import PhronesisMcpServer
from phronesis.mcp.server_spec import McpServerSpec
from phronesis.mcp.transport import StdioTransport


@pytest.fixture
def stdio_spec() -> McpServerSpec:
    """A canned :class:`McpServerSpec` with a stdio transport."""
    return McpServerSpec(
        name="fixture",
        transport=StdioTransport(command="python", args=("-V",)),
    )


@asynccontextmanager
async def connected_client(
    server: PhronesisMcpServer,
    spec: McpServerSpec,
) -> AsyncIterator[McpClient]:
    """Yield a live :class:`McpClient` bound to ``server`` via in-memory loopback."""
    lowlevel = server._build_lowlevel_server()
    session_ctx = create_connected_server_and_client_session(lowlevel)
    session: ClientSession = await session_ctx.__aenter__()

    client = McpClient(
        spec=spec,
        session=session,
        client_id=mcp_client_id_generator.from_canonical(f"phronesis.mcp.clients.{spec.name}"),
    )

    try:
        yield client
    finally:
        await session_ctx.__aexit__(None, None, None)


@pytest.fixture
def make_connected_client() -> Any:
    """Provide the :func:`connected_client` async context manager."""
    return connected_client
