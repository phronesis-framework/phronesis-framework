"""Span creation primitives for Phronesis components.

Exposes the ``start_span`` and ``start_span_async`` context managers as
the recommended way of producing spans from framework code.

When the ``obs`` extra is not installed, both context managers yield a
:class:`phronesis.obs._noop._NoopSpan` so call sites never need to
branch on whether OpenTelemetry is available.

When the extra is installed, the underlying OpenTelemetry tracer takes
care of recording exceptions and setting the span status to ``ERROR``
on uncaught exceptions inside the ``with`` block.

Span names follow the ``phronesis.<component>.<operation>`` convention
documented in the obs design notes.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from phronesis.obs._detect import OBS_AVAILABLE
from phronesis.obs._noop import _NoopSpan

_TRACER_NAME = "phronesis"


@contextmanager
def start_span(name: str, *, attributes: dict[str, Any] | None = None) -> Iterator[Any]:
    """Open a span named ``name`` as the current span.

    When the ``obs`` extra is not installed, yields a no-op span and
    performs no other work. Otherwise delegates to OpenTelemetry's
    ``start_as_current_span``, which records any uncaught exception
    inside the ``with`` block and marks the span status as ``ERROR``.
    """
    if not OBS_AVAILABLE:
        yield _NoopSpan()

        return

    from opentelemetry import trace

    tracer = trace.get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span(name, attributes=attributes) as span:
        yield span


@asynccontextmanager
async def start_span_async(
    name: str, *, attributes: dict[str, Any] | None = None
) -> AsyncIterator[Any]:
    """Async counterpart of :func:`start_span`.

    The semantics match the synchronous variant; this version exists so
    callers in ``async def`` functions can use ``async with`` without
    bouncing through a sync context manager.
    """
    if not OBS_AVAILABLE:
        yield _NoopSpan()

        return

    from opentelemetry import trace

    tracer = trace.get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span(name, attributes=attributes) as span:
        yield span
