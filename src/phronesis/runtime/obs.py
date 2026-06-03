"""Observability primitives for the runtime layer.

The runtime emits OpenTelemetry spans with the
``phronesis.runtime.<mode>`` naming convention and a closed set of
attribute names declared here. Metrics live as module-level counters and
histograms patterned after :mod:`phronesis.obs.metrics`: they start as
no-ops and are bound to real instruments when ``configure_obs`` runs.

Span helpers wrap :func:`phronesis.obs.spans.start_span_async` so callers
in modes only need to provide a mode name and a dictionary of extra
attributes.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any, Final

from phronesis.obs.spans import start_span_async

# Attribute names -----------------------------------------------------

RUNTIME_MODE: Final[str] = "runtime.mode"
RUNTIME_RUN_ID: Final[str] = "runtime.run_id"
RUNTIME_PARENT_ID: Final[str] = "runtime.parent_id"
RUNTIME_CHILDREN_COUNT: Final[str] = "runtime.children.count"
RUNTIME_ITERATION: Final[str] = "runtime.iteration"
RUNTIME_ROUTE: Final[str] = "runtime.route"
RUNTIME_HANDOFF_FROM: Final[str] = "runtime.handoff.from"
RUNTIME_HANDOFF_TO: Final[str] = "runtime.handoff.to"
RUNTIME_CANCELLED: Final[str] = "runtime.cancelled"
RUNTIME_SUCCESS: Final[str] = "runtime.success"


# Metric instrument placeholders --------------------------------------


class _NoopInstrument:
    """No-op counter/histogram, replaced by real instruments at configure_obs."""

    __slots__ = ()

    def add(self, _amount: float, _attributes: dict[str, Any] | None = None) -> None:
        return None

    def record(self, _amount: float, _attributes: dict[str, Any] | None = None) -> None:
        return None


_NOOP: _NoopInstrument = _NoopInstrument()

executions_total: _NoopInstrument = _NOOP
duration: _NoopInstrument = _NOOP
children_count: _NoopInstrument = _NOOP
iterations: _NoopInstrument = _NOOP
cancellations_total: _NoopInstrument = _NOOP


def _build_registry(meter: Any) -> None:  # pragma: no cover - wired by configure_obs
    """Bind runtime metric module attributes to real instruments."""
    global executions_total, duration, children_count, iterations, cancellations_total

    executions_total = meter.create_counter("phronesis.runtime.executions_total")
    duration = meter.create_histogram("phronesis.runtime.duration", unit="s")
    children_count = meter.create_histogram("phronesis.runtime.children_count")
    iterations = meter.create_histogram("phronesis.runtime.iterations")
    cancellations_total = meter.create_counter("phronesis.runtime.cancellations_total")


# Span helper ---------------------------------------------------------


@asynccontextmanager
async def runtime_span(
    mode: str,
    *,
    run_id: str | None = None,
    parent_id: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> AsyncIterator[Any]:
    """Open a ``phronesis.runtime.<mode>`` span with the standard attribute set."""
    attrs: dict[str, Any] = {RUNTIME_MODE: mode}

    if run_id is not None:
        attrs[RUNTIME_RUN_ID] = run_id

    if parent_id is not None:
        attrs[RUNTIME_PARENT_ID] = parent_id

    if extra:
        attrs.update(dict(extra))

    async with start_span_async(f"phronesis.runtime.{mode}", attributes=attrs) as span:
        yield span
