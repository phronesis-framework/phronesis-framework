"""High-level MCP client tailored to phronesis agents.

A :class:`McpClient` opens an MCP session against a single server
described by a :class:`McpServerSpec`, performs the protocol
handshake, and exposes :meth:`list_tools` returning a tuple of
phronesis :class:`Tool` instances ready to be injected into an
:class:`Agent` via :meth:`Agent.with_added_tools`.

The class is intentionally an async context manager: opening and
closing the underlying SDK streams is non-trivial and must be done
through the SDK's own context managers so we honour their lifecycle
guarantees.

A single :class:`McpClient` is bound to one transport / one server.
Composing several MCP servers in one agent is done outside this
class by passing the merged tool tuple to ``with_added_tools``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Self

import mcp
import mcp.types as mcp_types
from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamablehttp_client

from phronesis.mcp._adapt import mcp_tool_to_phronesis_tool
from phronesis.mcp.errors import McpConnectionError, McpProtocolError
from phronesis.mcp.ids import McpClientId, mcp_client_id_generator
from phronesis.mcp.obs import mcp_span
from phronesis.mcp.server_spec import McpServerSpec
from phronesis.mcp.transport import HttpTransport, StdioTransport
from phronesis.obs.attributes import (
    MCP_CLIENT_ID,
    MCP_SERVER_ID,
    MCP_SERVER_NAME,
    MCP_TRANSPORT,
)
from phronesis.tools.tool import Tool


def _client_id_for(spec: McpServerSpec) -> McpClientId:
    """Derive a stable :class:`McpClientId` from a server spec."""
    segment = spec.server_id.canonical.rsplit(".", 1)[-1]

    return mcp_client_id_generator.from_canonical(f"phronesis.mcp.clients.{segment}")


def _transport_kind(transport: StdioTransport | HttpTransport) -> str:
    """Return a short string identifier for the transport kind."""
    if isinstance(transport, StdioTransport):
        return "stdio"

    return "http"


class McpClient:
    """Active MCP session against a single server.

    Instances are produced exclusively by the
    :meth:`connect` async context manager so the underlying SDK
    resources are always released.

    Attributes:
        spec: The :class:`McpServerSpec` that drove the connection.
        session: The live :class:`mcp.ClientSession`.
        server_id: The server's stable :class:`McpServerId`.
        client_id: The client's stable :class:`McpClientId`.
    """

    __slots__ = ("client_id", "server_id", "session", "spec")

    def __init__(
        self,
        *,
        spec: McpServerSpec,
        session: ClientSession,
        client_id: McpClientId,
    ) -> None:
        self.spec = spec
        self.session = session
        self.server_id = spec.server_id
        self.client_id = client_id

    @classmethod
    @asynccontextmanager
    async def connect(cls, spec: McpServerSpec) -> AsyncIterator[Self]:
        """Open a session against ``spec`` and yield a live :class:`McpClient`.

        On exit (normal or exceptional) the SDK streams and the
        underlying transport are closed cleanly.

        Raises:
            McpConnectionError: when the transport cannot be opened
                or the handshake fails.
        """
        transport = spec.transport
        client_id = _client_id_for(spec)
        stack = AsyncExitStack()

        try:
            if isinstance(transport, StdioTransport):
                params = StdioServerParameters(
                    command=transport.command,
                    args=list(transport.args),
                    env=dict(transport.env) if transport.env else None,
                )
                read, write = await stack.enter_async_context(stdio_client(params))
            else:
                read, write, _get_session_id = await stack.enter_async_context(
                    streamablehttp_client(
                        url=transport.url,
                        headers=dict(transport.headers) if transport.headers else None,
                    )
                )

            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
        except mcp.McpError as exc:
            await stack.aclose()

            raise McpProtocolError(
                f"MCP handshake failed for server {spec.name!r}: {exc}",
                details={"server": spec.name},
            ) from exc
        except Exception as exc:
            await stack.aclose()

            raise McpConnectionError(
                f"Failed to connect to MCP server {spec.name!r}: {exc}",
                details={"server": spec.name},
            ) from exc

        client = cls(spec=spec, session=session, client_id=client_id)

        try:
            yield client
        finally:
            await stack.aclose()

    async def list_tools(self) -> tuple[Tool, ...]:
        """Enumerate the remote tools and adapt each to a phronesis :class:`Tool`.

        Returns:
            A tuple of :class:`Tool` instances suitable for
            :meth:`Agent.with_added_tools`. Each tool's invocation
            forwards to this client's session.
        """
        extra = {
            MCP_SERVER_ID: self.server_id.canonical,
            MCP_SERVER_NAME: self.spec.name,
            MCP_CLIENT_ID: self.client_id.canonical,
            MCP_TRANSPORT: _transport_kind(self.spec.transport),
        }

        async with mcp_span("client.list_tools", extra=extra):
            result: mcp_types.ListToolsResult = await self.session.list_tools()

        return tuple(
            mcp_tool_to_phronesis_tool(self, mcp_tool, server_name=self.spec.name)
            for mcp_tool in result.tools
        )
