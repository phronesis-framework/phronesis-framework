"""Identifier types for MCP servers and clients.

Two distinct identifiers are emitted by the :mod:`phronesis.mcp`
package:

* :class:`McpServerId` - identifies an MCP server, either a remote
  server described by a :class:`McpServerSpec` or the local
  :class:`phronesis.mcp.PhronesisMcpServer`. Prefix ``"MSID"``.
* :class:`McpClientId` - identifies an active :class:`McpClient`
  session. Prefix ``"MCID"``.

Process-wide :class:`IdGenerator` singletons are exposed for parsing
canonical strings without instantiating a generator at the call site.
"""

from __future__ import annotations

from phronesis._internal.ids.generator import IdGenerator
from phronesis._internal.ids.id import Id


class McpServerId(Id):
    """Stable internal identifier for an MCP server.

    Subclass of :class:`phronesis._internal.ids.id.Id` with the short
    prefix ``"MSID"``. Instances are created from a canonical string
    (e.g. ``"phronesis.mcp.servers.filesystem"``) and validated by the
    base class.
    """

    prefix = "MSID"


class McpClientId(Id):
    """Stable internal identifier for an active MCP client session.

    Subclass of :class:`phronesis._internal.ids.id.Id` with the short
    prefix ``"MCID"``. The canonical form is typically derived from
    the connected server's name (e.g.
    ``"phronesis.mcp.clients.filesystem"``).
    """

    prefix = "MCID"


mcp_server_id_generator: IdGenerator[McpServerId] = IdGenerator(McpServerId)
"""Process-wide :class:`IdGenerator` bound to :class:`McpServerId`."""

mcp_client_id_generator: IdGenerator[McpClientId] = IdGenerator(McpClientId)
"""Process-wide :class:`IdGenerator` bound to :class:`McpClientId`."""
