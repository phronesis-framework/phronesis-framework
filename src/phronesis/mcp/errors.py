"""Error hierarchy for the :mod:`phronesis.mcp` package.

Every error in this module inherits from :class:`McpError`, which in
turn extends :class:`phronesis.errors.PhronesisError` so callers can
``except McpError`` to catch any MCP-related failure originating in
phronesis code.

Each subclass carries a stable ``code`` attribute mirroring the style
used by :class:`phronesis.tools.errors.ToolError` and
:class:`phronesis.memory.errors.MemoryError`. MCP errors are
**not** serialised back to the model: they are framework-side
failures surfaced to the caller of :class:`McpClient` or to the
:class:`PhronesisMcpServer` runtime.
"""

from __future__ import annotations

from phronesis.errors import PhronesisError


class McpError(PhronesisError):
    """Base class for every failure originating in :mod:`phronesis.mcp`."""

    code: str = "mcp_error"


class McpConnectionError(McpError):
    """Could not establish or sustain a connection to an MCP server.

    Covers transport-level failures (process spawn errors, refused
    HTTP connections, broken pipes) as well as protocol handshake
    failures. The original exception is preserved via ``__cause__``.
    """

    code = "mcp_connection_error"


class McpProtocolError(McpError):
    """The remote peer returned an MCP message that violates the spec.

    Used when the SDK surfaces a malformed response or when the
    adaptation layer cannot translate the payload into a phronesis
    primitive.
    """

    code = "mcp_protocol_error"


class McpTimeoutError(McpError):
    """An MCP operation exceeded its allotted time budget."""

    code = "mcp_timeout"


class McpToolNotFoundError(McpError):
    """The requested tool is not exposed by the connected MCP server."""

    code = "mcp_tool_not_found"
