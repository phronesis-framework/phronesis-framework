"""Closed catalog of standard metric instruments.

Holds the registry of OpenTelemetry counters and histograms automatically
created when ``configure_obs`` runs, along with no-op fallbacks used
when the ``obs`` extra is not installed or the meter has not yet been
built.

The catalog is exposed as module-level attributes so call sites can
write::

    from phronesis.obs import metrics

    metrics.tool_invocations.add(1, attributes={"tool.id": tid})
    metrics.provider_duration.record(0.42, attributes={"provider.name": "anthropic"})

Each attribute starts as a :class:`_NoopInstrument` and is rebound to a
real OpenTelemetry instrument by :func:`_build_registry` during
``configure_obs``.

Catalog:

Tools
    ``tool_invocations``, ``tool_duration``, ``tool_errors``

Providers
    ``provider_requests``, ``provider_tokens_input``,
    ``provider_tokens_output``, ``provider_duration``

Agents
    ``agent_runs``, ``agent_run_duration``, ``agent_tool_calls_per_run``

Pipelines
    ``pipeline_runs``, ``pipeline_run_duration``

Retries
    ``retry_attempts``
"""

from __future__ import annotations

from typing import Any, Protocol


class _CounterLike(Protocol):
    def add(self, amount: float, attributes: dict[str, Any] | None = None) -> None: ...


class _HistogramLike(Protocol):
    def record(self, amount: float, attributes: dict[str, Any] | None = None) -> None: ...


class _NoopInstrument:
    """Fallback that accepts ``add`` and ``record`` calls without effect."""

    __slots__ = ()

    def add(self, amount: float, attributes: dict[str, Any] | None = None) -> None:
        return None

    def record(self, amount: float, attributes: dict[str, Any] | None = None) -> None:
        return None


_NOOP: _NoopInstrument = _NoopInstrument()

# Tool metrics --------------------------------------------------------

tool_invocations: _CounterLike = _NOOP
tool_duration: _HistogramLike = _NOOP
tool_errors: _CounterLike = _NOOP

# Provider metrics ----------------------------------------------------

provider_requests: _CounterLike = _NOOP
provider_tokens_input: _CounterLike = _NOOP
provider_tokens_output: _CounterLike = _NOOP
provider_duration: _HistogramLike = _NOOP

# Agent metrics -------------------------------------------------------

agent_runs: _CounterLike = _NOOP
agent_run_duration: _HistogramLike = _NOOP
agent_tool_calls_per_run: _HistogramLike = _NOOP

# Pipeline metrics ----------------------------------------------------

pipeline_runs: _CounterLike = _NOOP
pipeline_run_duration: _HistogramLike = _NOOP

# Retry metrics -------------------------------------------------------

retry_attempts: _CounterLike = _NOOP


def _build_registry(meter: Any) -> None:
    """Bind module-level attributes to real OpenTelemetry instruments."""
    global tool_invocations, tool_duration, tool_errors
    global provider_requests, provider_tokens_input, provider_tokens_output, provider_duration
    global agent_runs, agent_run_duration, agent_tool_calls_per_run
    global pipeline_runs, pipeline_run_duration
    global retry_attempts

    tool_invocations = meter.create_counter("phronesis.tool.invocations")
    tool_duration = meter.create_histogram("phronesis.tool.duration", unit="s")
    tool_errors = meter.create_counter("phronesis.tool.errors")

    provider_requests = meter.create_counter("phronesis.provider.requests")
    provider_tokens_input = meter.create_counter("phronesis.provider.tokens.input")
    provider_tokens_output = meter.create_counter("phronesis.provider.tokens.output")
    provider_duration = meter.create_histogram("phronesis.provider.duration", unit="s")

    agent_runs = meter.create_counter("phronesis.agent.runs")
    agent_run_duration = meter.create_histogram("phronesis.agent.run_duration", unit="s")
    agent_tool_calls_per_run = meter.create_histogram("phronesis.agent.tool_calls_per_run")

    pipeline_runs = meter.create_counter("phronesis.pipeline.runs")
    pipeline_run_duration = meter.create_histogram("phronesis.pipeline.run_duration", unit="s")

    retry_attempts = meter.create_counter("phronesis.retry.attempts")


def _reset_registry() -> None:
    """Rebind every instrument to the no-op fallback. Test only."""
    global tool_invocations, tool_duration, tool_errors
    global provider_requests, provider_tokens_input, provider_tokens_output, provider_duration
    global agent_runs, agent_run_duration, agent_tool_calls_per_run
    global pipeline_runs, pipeline_run_duration
    global retry_attempts

    tool_invocations = _NOOP
    tool_duration = _NOOP
    tool_errors = _NOOP

    provider_requests = _NOOP
    provider_tokens_input = _NOOP
    provider_tokens_output = _NOOP
    provider_duration = _NOOP

    agent_runs = _NOOP
    agent_run_duration = _NOOP
    agent_tool_calls_per_run = _NOOP

    pipeline_runs = _NOOP
    pipeline_run_duration = _NOOP

    retry_attempts = _NOOP
