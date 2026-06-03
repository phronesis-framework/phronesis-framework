"""Declarative description of an external MCP server.

A :class:`McpServerSpec` is the pure-data side of an MCP client
connection: it identifies the server by name, picks a transport, and
optionally fixes a stable :class:`McpServerId`. It does **not** open
the connection - that is the job of :class:`McpClient`.

The spec is frozen so a single instance can be reused across multiple
:meth:`McpClient.connect` calls without risk of mutation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from phronesis.mcp.ids import McpServerId
from phronesis.mcp.transport import Transport

_INVALID_CHARS = re.compile(r"[^a-z0-9_]+")


def _canonical_from_name(name: str) -> str:
    """Derive a canonical id segment from a free-form server name."""
    lowered = name.strip().lower()
    cleaned = _INVALID_CHARS.sub("_", lowered).strip("_")

    if not cleaned:
        raise ValueError(f"Cannot derive canonical id from server name: {name!r}.")

    if cleaned[0].isdigit():
        cleaned = f"_{cleaned}"

    return cleaned


def _default_server_id(name: str) -> McpServerId:
    """Build a default :class:`McpServerId` from a server name."""
    segment = _canonical_from_name(name)

    return McpServerId(f"phronesis.mcp.servers.{segment}")


@dataclass(frozen=True, slots=True)
class McpServerSpec:
    """Static description of an MCP server the client can connect to.

    Attributes:
        name: Human-readable server name (e.g. ``"filesystem"``).
            Used in span attributes and to derive a default
            :class:`McpServerId` when ``server_id`` is omitted.
        transport: Concrete :data:`Transport` used to reach the
            server.
        server_id: Optional stable :class:`McpServerId`. When
            ``None`` (the default), an id is derived from ``name``
            via the ``phronesis.mcp.servers.<name>`` template.
    """

    name: str
    transport: Transport
    server_id: McpServerId = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.server_id is None:
            object.__setattr__(self, "server_id", _default_server_id(self.name))
