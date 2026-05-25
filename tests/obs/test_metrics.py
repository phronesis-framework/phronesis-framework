"""Tests for the metrics registry no-op fallback and catalog shape."""

from __future__ import annotations

from phronesis.obs import metrics as metrics_module
from phronesis.obs.metrics import _NOOP, _NoopInstrument, _reset_registry

_COUNTER_NAMES = (
    "tool_invocations",
    "tool_errors",
    "provider_requests",
    "provider_tokens_input",
    "provider_tokens_output",
    "agent_runs",
    "pipeline_runs",
    "retry_attempts",
)

_HISTOGRAM_NAMES = (
    "tool_duration",
    "provider_duration",
    "agent_run_duration",
    "agent_tool_calls_per_run",
    "pipeline_run_duration",
)


class TestNoopInstrument:
    def test_add_returns_none(self) -> None:
        assert _NoopInstrument().add(1) is None

    def test_add_with_attributes_returns_none(self) -> None:
        assert _NoopInstrument().add(1, {"k": "v"}) is None

    def test_record_returns_none(self) -> None:
        assert _NoopInstrument().record(1.5) is None

    def test_record_with_attributes_returns_none(self) -> None:
        assert _NoopInstrument().record(1.5, {"k": "v"}) is None


class TestNoopRegistryDefaults:
    def test_all_counters_default_to_noop(self) -> None:
        for name in _COUNTER_NAMES:
            assert getattr(metrics_module, name) is _NOOP, name

    def test_all_histograms_default_to_noop(self) -> None:
        for name in _HISTOGRAM_NAMES:
            assert getattr(metrics_module, name) is _NOOP, name

    def test_counter_call_is_noop(self) -> None:
        metrics_module.tool_invocations.add(1, attributes={"tool.id": "x"})

    def test_histogram_call_is_noop(self) -> None:
        metrics_module.tool_duration.record(0.42, attributes={"tool.id": "x"})


class TestResetRegistry:
    def test_reset_restores_noop_after_build(self) -> None:
        sentinel = object()
        metrics_module.tool_invocations = sentinel  # type: ignore[assignment]

        _reset_registry()

        assert metrics_module.tool_invocations is _NOOP

    def test_reset_is_idempotent(self) -> None:
        _reset_registry()
        _reset_registry()

        for name in _COUNTER_NAMES + _HISTOGRAM_NAMES:
            assert getattr(metrics_module, name) is _NOOP
