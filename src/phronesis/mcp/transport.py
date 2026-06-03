"""Transport descriptors for MCP client connections.

A :data:`Transport` describes *how* a :class:`McpClient` connects to
a remote MCP server. v1 supports two flavours:

* :class:`StdioTransport` - spawns a child process and speaks the
  MCP framing over its stdin/stdout. The standard for local servers.
* :class:`HttpTransport` - opens a Streamable HTTP connection to a
  remote URL. The standard for hosted servers.

Both classes are frozen dataclasses so they can be shared safely
across tasks and used as dictionary keys when needed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TypeAlias


@dataclass(frozen=True, slots=True)
class StdioTransport:
    """Spawn an MCP server as a child process and talk over stdio.

    Attributes:
        command: Executable to launch (e.g. ``"npx"``, ``"python"``).
        args: Positional arguments passed to ``command``.
        env: Extra environment variables merged on top of the
            inherited environment when launching the child process.
    """

    command: str
    args: tuple[str, ...] = ()
    env: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class HttpTransport:
    """Open a Streamable HTTP connection to a remote MCP server.

    Attributes:
        url: Endpoint URL exposing the Streamable HTTP MCP transport.
        headers: Extra HTTP headers sent on every request (typically
            for authentication).
    """

    url: str
    headers: Mapping[str, str] = field(default_factory=dict)


Transport: TypeAlias = StdioTransport | HttpTransport
"""Discriminated union of supported MCP client transports."""
