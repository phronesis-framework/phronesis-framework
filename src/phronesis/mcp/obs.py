"""Observability primitives for the MCP layer.

The MCP layer emits OpenTelemetry spans with the
``phronesis.mcp.<operation>`` naming convention and uses the closed
set of attribute names declared in :mod:`phronesis.obs.attributes`
(the ``MCP_*`` constants).

The :func:`mcp_span` helper wraps :func:`phronesis.obs.spans.start_span_async`
so callers in the client/server layers only need to provide an
operation name and a dictionary of extra attributes.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any

from phronesis.obs.attributes import MCP_OPERATION
from phronesis.obs.spans import start_span_async


@asynccontextmanager
async def mcp_span(
    operation: str,
    *,
    extra: Mapping[str, Any] | None = None,
) -> AsyncIterator[Any]:
    """Open a ``phronesis.mcp.<operation>`` span with the standard attribute set.

    The ``mcp.operation`` attribute is always set to ``operation``.
    Any keys passed via ``extra`` are layered on top and override
    the defaults if they collide.

    Args:
        operation: Short operation identifier (e.g.
            ``"client.list_tools"``, ``"server.call_tool"``).
        extra: Optional mapping of additional attributes (typically
            built from the ``MCP_*`` constants of
            :mod:`phronesis.obs.attributes`).

    Yields:
        The active span (real OpenTelemetry span or no-op fallback
        when the ``obs`` extra is not installed).
    """
    attrs: dict[str, Any] = {MCP_OPERATION: operation}

    if extra:
        attrs.update(dict(extra))

    async with start_span_async(f"phronesis.mcp.{operation}", attributes=attrs) as span:
        yield span
