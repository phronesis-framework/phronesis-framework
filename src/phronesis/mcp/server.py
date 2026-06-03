"""Expose a tuple of phronesis :class:`Tool` instances as an MCP server.

A :class:`PhronesisMcpServer` wraps a low-level :class:`mcp.server.Server`
configured with two handlers:

* ``list_tools`` - projects every wrapped :class:`Tool` to an
  :class:`mcp.types.Tool` via :func:`phronesis_tool_to_mcp_definition`.
* ``call_tool`` - looks the requested tool up by name and invokes it
  through :meth:`Tool.invoke`.

Two transports are supported in v1:

* :meth:`run_stdio` - speaks the MCP framing over the current
  process' stdin/stdout. The standard mode for local tools that a
  parent agent spawns as a child process.
* :meth:`run_http` - serves the Streamable HTTP transport using
  ``uvicorn`` and ``starlette`` (both shipped with the ``mcp`` SDK).

Errors raised by a tool's :meth:`Tool.invoke` are caught and projected
to an ``isError=True`` MCP result so the caller's run is not aborted.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, cast

import mcp.types as mcp_types
from mcp.server.lowlevel import Server

from phronesis.mcp._adapt import (
    payload_to_content_blocks,
    phronesis_tool_to_mcp_definition,
)
from phronesis.mcp.ids import McpServerId, mcp_server_id_generator
from phronesis.mcp.obs import mcp_span
from phronesis.mcp.server_spec import _canonical_from_name
from phronesis.obs.attributes import (
    MCP_SERVER_ID,
    MCP_SERVER_NAME,
    MCP_TOOL_NAME,
)
from phronesis.tools.errors import ToolError
from phronesis.tools.tool import Tool


def _default_server_id(name: str) -> McpServerId:
    """Build a default :class:`McpServerId` from a server name."""
    segment = _canonical_from_name(name)

    return mcp_server_id_generator.from_canonical(f"phronesis.mcp.servers.{segment}")


@dataclass(frozen=True, slots=True)
class PhronesisMcpServer:
    """Local MCP server publishing a fixed set of phronesis tools.

    Use the :func:`mcp_server` factory in user code instead of
    constructing this dataclass directly.

    Attributes:
        name: Human-readable server name, sent to clients during the
            MCP handshake.
        tools: Frozen tuple of :class:`Tool` instances published by
            the server.
        server_id: Stable :class:`McpServerId` derived from ``name``
            unless explicitly overridden.
    """

    name: str
    tools: tuple[Tool, ...]
    server_id: McpServerId
    _by_name: dict[str, Tool] = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self) -> None:
        by_name: dict[str, Tool] = {}

        for tool in self.tools:
            tool_name = str(tool.spec.name)

            if tool_name in by_name:
                raise ValueError(
                    f"Duplicate tool name in PhronesisMcpServer({self.name!r}): {tool_name!r}."
                )

            by_name[tool_name] = tool

        object.__setattr__(self, "_by_name", by_name)

    def _build_lowlevel_server(self) -> Server[Any, Any]:
        """Build a :class:`mcp.server.lowlevel.Server` wired to this instance."""
        server: Server[Any, Any] = Server(self.name)
        tools_index = self._by_name
        server_id_canonical = self.server_id.canonical
        server_name = self.name

        async def _list_tools() -> list[mcp_types.Tool]:
            return [phronesis_tool_to_mcp_definition(tool) for tool in self.tools]

        async def _call_tool(
            tool_name: str,
            arguments: dict[str, Any],
        ) -> mcp_types.CallToolResult:
            extra = {
                MCP_SERVER_ID: server_id_canonical,
                MCP_SERVER_NAME: server_name,
                MCP_TOOL_NAME: tool_name,
            }

            async with mcp_span("server.call_tool", extra=extra):
                tool = tools_index.get(tool_name)

                if tool is None:
                    return mcp_types.CallToolResult(
                        content=cast(
                            list[mcp_types.ContentBlock],
                            [
                                mcp_types.TextContent(
                                    type="text",
                                    text=f"Unknown tool: {tool_name!r}.",
                                )
                            ],
                        ),
                        isError=True,
                    )

                try:
                    result = tool.invoke(arguments)

                    if tool.is_async:
                        result = await result
                except ToolError as exc:
                    return mcp_types.CallToolResult(
                        content=cast(
                            list[mcp_types.ContentBlock],
                            [mcp_types.TextContent(type="text", text=exc.message)],
                        ),
                        isError=True,
                    )

            return mcp_types.CallToolResult(
                content=cast(list[mcp_types.ContentBlock], payload_to_content_blocks(result)),
                isError=False,
            )

        server.list_tools()(_list_tools)  # type: ignore[no-untyped-call]
        server.call_tool()(_call_tool)

        return server

    async def run_stdio(self) -> None:
        """Serve over the stdio transport. Blocks until the client disconnects.

        Intended for the common case where a parent process spawns
        this server as a child and talks to it over its stdin/stdout.
        """
        from mcp.server.stdio import stdio_server

        server = self._build_lowlevel_server()

        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    async def run_http(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 8000,
    ) -> None:
        """Serve over the Streamable HTTP transport.

        Args:
            host: Interface to bind the HTTP server to.
            port: TCP port to listen on.
        """
        import contextlib

        import uvicorn
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
        from starlette.applications import Starlette
        from starlette.routing import Mount

        server = self._build_lowlevel_server()
        manager = StreamableHTTPSessionManager(app=server, stateless=False)

        @contextlib.asynccontextmanager
        async def _lifespan(_app: Starlette):  # type: ignore[no-untyped-def]
            async with manager.run():
                yield

        app = Starlette(
            routes=[Mount("/", app=manager.handle_request)],
            lifespan=_lifespan,
        )

        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        await uvicorn.Server(config).serve()


def mcp_server(
    *,
    name: str,
    tools: Iterable[Tool],
    server_id: McpServerId | None = None,
) -> PhronesisMcpServer:
    """Build a :class:`PhronesisMcpServer` from a tuple of phronesis tools.

    Args:
        name: Human-readable server name surfaced to MCP clients.
        tools: Iterable of :class:`Tool` instances to publish.
        server_id: Optional stable :class:`McpServerId`. Defaults to
            ``phronesis.mcp.servers.<name>``.

    Returns:
        A frozen :class:`PhronesisMcpServer` ready to be served via
        :meth:`run_stdio` or :meth:`run_http`.
    """
    resolved_id = server_id if server_id is not None else _default_server_id(name)

    return PhronesisMcpServer(
        name=name,
        tools=tuple(tools),
        server_id=resolved_id,
    )
