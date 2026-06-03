"""Public API of the :mod:`phronesis.mcp` package.

This package exposes phronesis' integration with the Model Context
Protocol (MCP), the open standard for connecting agents to tool
servers. Two surfaces are provided:

* **Client** - :class:`McpClient` opens a session against an external
  MCP server described by a :class:`McpServerSpec` and exposes its
  tools as phronesis :class:`Tool` instances ready to be injected
  into an :class:`~phronesis.agents.Agent`.
* **Server** - :func:`mcp_server` builds a :class:`PhronesisMcpServer`
  publishing a tuple of phronesis tools over MCP, so any MCP-aware
  client (Claude Desktop, IDEs, other agents) can consume them.

Only Tools are supported in v1; resources, prompts and sampling are
deferred. Two transports are supported: stdio (local processes) and
Streamable HTTP (hosted servers).

Only names listed in ``__all__`` are part of the public contract.
Anything else is internal and may change without notice.
"""

from __future__ import annotations

from phronesis.mcp.client import McpClient
from phronesis.mcp.errors import (
    McpConnectionError,
    McpError,
    McpProtocolError,
    McpTimeoutError,
    McpToolNotFoundError,
)
from phronesis.mcp.ids import (
    McpClientId,
    McpServerId,
    mcp_client_id_generator,
    mcp_server_id_generator,
)
from phronesis.mcp.obs import mcp_span
from phronesis.mcp.server import PhronesisMcpServer, mcp_server
from phronesis.mcp.server_spec import McpServerSpec
from phronesis.mcp.transport import HttpTransport, StdioTransport, Transport

__all__ = [
    "HttpTransport",
    "McpClient",
    "McpClientId",
    "McpConnectionError",
    "McpError",
    "McpProtocolError",
    "McpServerId",
    "McpServerSpec",
    "McpTimeoutError",
    "McpToolNotFoundError",
    "PhronesisMcpServer",
    "StdioTransport",
    "Transport",
    "mcp_client_id_generator",
    "mcp_server",
    "mcp_server_id_generator",
    "mcp_span",
]
