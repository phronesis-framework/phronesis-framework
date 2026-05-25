"""Span creation primitives for Phronesis components.

Exposes the ``start_span`` and ``start_span_async`` context managers and
the ``traced`` decorator as the recommended way of producing spans from
framework code.

When the ``obs`` extra is not installed, both context managers yield a
:class:`phronesis.obs._noop._NoopSpan` and ``traced`` returns the
wrapped function unchanged. Call sites never need to branch on whether
OpenTelemetry is available, and uninstrumented runs pay zero overhead.

When the extra is installed, the underlying OpenTelemetry tracer takes
care of recording exceptions and setting the span status to ``ERROR``
on uncaught exceptions inside the ``with`` block.

Span names follow the ``phronesis.<component>.<operation>`` convention
documented in the obs design notes.
"""

from __future__ import annotations

import functools
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from inspect import iscoroutinefunction
from typing import Any, TypeVar, cast

from phronesis.obs._detect import OBS_AVAILABLE
from phronesis.obs._noop import _NoopSpan

_TRACER_NAME = "phronesis"

F = TypeVar("F", bound=Callable[..., Any])


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


def traced(
    name: str,
    *,
    attributes_from: Callable[..., dict[str, Any]] | None = None,
) -> Callable[[F], F]:
    """Decorate a function so each call is wrapped in a span.

    When the ``obs`` extra is not installed, the decorator returns the
    function unchanged so instrumented call sites pay zero overhead at
    runtime.

    The wrapper is selected automatically based on whether the function
    is a coroutine: ``async def`` functions get ``start_span_async`` and
    plain ``def`` functions get ``start_span``.

    ``attributes_from``, when provided, is invoked with the same
    ``*args`` and ``**kwargs`` passed to the wrapped function and must
    return a dictionary of attribute values applied to the span at
    creation time.
    """

    def decorator(fn: F) -> F:
        if not OBS_AVAILABLE:
            return fn

        if iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                attrs = attributes_from(*args, **kwargs) if attributes_from else None

                async with start_span_async(name, attributes=attrs):
                    return await fn(*args, **kwargs)

            return cast(F, async_wrapper)

        @functools.wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            attrs = attributes_from(*args, **kwargs) if attributes_from else None

            with start_span(name, attributes=attrs):
                return fn(*args, **kwargs)

        return cast(F, sync_wrapper)

    return decorator


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
