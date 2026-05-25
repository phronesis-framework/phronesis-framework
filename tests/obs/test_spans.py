"""Tests for ``start_span`` and ``start_span_async``."""

from __future__ import annotations

from typing import Any

import pytest

from phronesis.obs import spans as spans_module
from phronesis.obs._detect import OBS_AVAILABLE
from phronesis.obs._noop import _NoopSpan
from phronesis.obs.config import configure_obs
from phronesis.obs.spans import current_trace_id, start_span, start_span_async


class _SpyExporter:
    def __init__(self) -> None:
        self.exported: list[Any] = []

    def export(self, spans: Any) -> Any:
        from opentelemetry.sdk.trace.export import SpanExportResult

        self.exported.extend(spans)

        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        return None

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


class TestStartSpanNoopMode:
    def test_yields_noop_span_when_obs_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(spans_module, "OBS_AVAILABLE", False)

        with start_span("phronesis.test.op") as span:
            assert isinstance(span, _NoopSpan)

    def test_attributes_accepted_and_ignored_in_noop_mode(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(spans_module, "OBS_AVAILABLE", False)

        with start_span("phronesis.test.op", attributes={"k": "v"}) as span:
            assert isinstance(span, _NoopSpan)

    def test_exception_propagates_through_noop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(spans_module, "OBS_AVAILABLE", False)

        with pytest.raises(ValueError, match="boom"), start_span("phronesis.test.op"):
            raise ValueError("boom")


@pytest.mark.skipif(not OBS_AVAILABLE, reason="obs extra not installed")
class TestStartSpanActiveMode:
    def test_emits_span_with_expected_name(self) -> None:
        spy = _SpyExporter()
        configure_obs(exporter_instance=spy)

        with start_span("phronesis.test.op"):
            pass

        assert len(spy.exported) == 1
        assert spy.exported[0].name == "phronesis.test.op"

    def test_initial_attributes_are_applied(self) -> None:
        spy = _SpyExporter()
        configure_obs(exporter_instance=spy)

        with start_span("phronesis.test.op", attributes={"k": "v", "n": 1}):
            pass

        attrs = dict(spy.exported[0].attributes)

        assert attrs["k"] == "v"
        assert attrs["n"] == 1

    def test_set_attribute_inside_block_is_recorded(self) -> None:
        spy = _SpyExporter()
        configure_obs(exporter_instance=spy)

        with start_span("phronesis.test.op") as span:
            span.set_attribute("dynamic", "yes")

        assert dict(spy.exported[0].attributes)["dynamic"] == "yes"

    def test_uncaught_exception_is_recorded_and_status_is_error(self) -> None:
        from opentelemetry.trace import StatusCode

        spy = _SpyExporter()
        configure_obs(exporter_instance=spy)

        with pytest.raises(RuntimeError, match="boom"), start_span("phronesis.test.fail"):
            raise RuntimeError("boom")

        exported = spy.exported[0]

        assert exported.status.status_code == StatusCode.ERROR
        event_names = [event.name for event in exported.events]
        assert "exception" in event_names


class TestStartSpanAsyncNoopMode:
    async def test_yields_noop_span_when_obs_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(spans_module, "OBS_AVAILABLE", False)

        async with start_span_async("phronesis.test.op") as span:
            assert isinstance(span, _NoopSpan)

    async def test_exception_propagates_through_noop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(spans_module, "OBS_AVAILABLE", False)

        with pytest.raises(ValueError, match="boom"):
            async with start_span_async("phronesis.test.op"):
                raise ValueError("boom")


class TestCurrentTraceIdNoopMode:
    def test_returns_none_when_obs_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(spans_module, "OBS_AVAILABLE", False)

        assert current_trace_id() is None


@pytest.mark.skipif(not OBS_AVAILABLE, reason="obs extra not installed")
class TestCurrentTraceIdActiveMode:
    def test_returns_none_without_active_span(self) -> None:
        configure_obs()

        assert current_trace_id() is None

    def test_returns_hex_string_inside_span(self) -> None:
        configure_obs()

        with start_span("phronesis.test.op"):
            trace_id = current_trace_id()

        assert trace_id is not None
        assert len(trace_id) == 32
        int(trace_id, 16)

    def test_matches_span_context_trace_id(self) -> None:
        from opentelemetry import trace

        configure_obs()

        with start_span("phronesis.test.op"):
            span = trace.get_current_span()
            expected = format(span.get_span_context().trace_id, "032x")
            actual = current_trace_id()

        assert actual == expected

    def test_returns_none_after_span_closes(self) -> None:
        configure_obs()

        with start_span("phronesis.test.op"):
            pass

        assert current_trace_id() is None


@pytest.mark.skipif(not OBS_AVAILABLE, reason="obs extra not installed")
class TestStartSpanAsyncActiveMode:
    async def test_emits_span_with_expected_name(self) -> None:
        spy = _SpyExporter()
        configure_obs(exporter_instance=spy)

        async with start_span_async("phronesis.test.async"):
            pass

        assert len(spy.exported) == 1
        assert spy.exported[0].name == "phronesis.test.async"

    async def test_initial_attributes_are_applied(self) -> None:
        spy = _SpyExporter()
        configure_obs(exporter_instance=spy)

        async with start_span_async("phronesis.test.async", attributes={"k": "v"}):
            pass

        assert dict(spy.exported[0].attributes)["k"] == "v"

    async def test_uncaught_exception_is_recorded_and_status_is_error(self) -> None:
        from opentelemetry.trace import StatusCode

        spy = _SpyExporter()
        configure_obs(exporter_instance=spy)

        with pytest.raises(RuntimeError, match="boom"):
            async with start_span_async("phronesis.test.async.fail"):
                raise RuntimeError("boom")

        exported = spy.exported[0]

        assert exported.status.status_code == StatusCode.ERROR
        event_names = [event.name for event in exported.events]
        assert "exception" in event_names
