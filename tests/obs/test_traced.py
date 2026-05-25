"""Tests for the ``@traced`` decorator."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from phronesis.obs import spans as spans_module
from phronesis.obs.config import configure_obs
from phronesis.obs.spans import traced


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


class TestTracedNoopMode:
    def test_returns_function_unchanged_when_obs_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(spans_module, "OBS_AVAILABLE", False)

        def fn(x: int) -> int:
            return x * 2

        wrapped = traced("phronesis.test.op")(fn)

        assert wrapped is fn
        assert wrapped(3) == 6

    def test_async_function_returned_unchanged_when_obs_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(spans_module, "OBS_AVAILABLE", False)

        async def fn(x: int) -> int:
            return x + 1

        wrapped = traced("phronesis.test.async")(fn)

        assert wrapped is fn
        assert asyncio.run(wrapped(4)) == 5


class TestTracedSyncActiveMode:
    def test_call_emits_span_with_expected_name(self) -> None:
        spy = _SpyExporter()
        configure_obs(exporter_instance=spy)

        @traced("phronesis.test.op")
        def fn(x: int) -> int:
            return x * 2

        assert fn(3) == 6
        assert len(spy.exported) == 1
        assert spy.exported[0].name == "phronesis.test.op"

    def test_exception_is_recorded_and_status_is_error(self) -> None:
        from opentelemetry.trace import StatusCode

        spy = _SpyExporter()
        configure_obs(exporter_instance=spy)

        @traced("phronesis.test.fail")
        def fn() -> None:
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            fn()

        exported = spy.exported[0]

        assert exported.status.status_code == StatusCode.ERROR

    def test_attributes_from_is_applied(self) -> None:
        spy = _SpyExporter()
        configure_obs(exporter_instance=spy)

        @traced("phronesis.test.op", attributes_from=lambda x, *, label: {"x": x, "label": label})
        def fn(x: int, *, label: str) -> int:
            return x

        fn(7, label="foo")

        attrs = dict(spy.exported[0].attributes)

        assert attrs["x"] == 7
        assert attrs["label"] == "foo"

    def test_wraps_preserves_name_and_doc(self) -> None:
        spy = _SpyExporter()
        configure_obs(exporter_instance=spy)

        @traced("phronesis.test.op")
        def fn(x: int) -> int:
            """Do a thing."""
            return x

        assert fn.__name__ == "fn"
        assert fn.__doc__ == "Do a thing."


class TestTracedAsyncActiveMode:
    async def test_call_emits_span_with_expected_name(self) -> None:
        spy = _SpyExporter()
        configure_obs(exporter_instance=spy)

        @traced("phronesis.test.async")
        async def fn(x: int) -> int:
            return x * 3

        assert await fn(4) == 12
        assert len(spy.exported) == 1
        assert spy.exported[0].name == "phronesis.test.async"

    async def test_exception_is_recorded_and_status_is_error(self) -> None:
        from opentelemetry.trace import StatusCode

        spy = _SpyExporter()
        configure_obs(exporter_instance=spy)

        @traced("phronesis.test.async.fail")
        async def fn() -> None:
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await fn()

        exported = spy.exported[0]

        assert exported.status.status_code == StatusCode.ERROR

    async def test_attributes_from_is_applied(self) -> None:
        spy = _SpyExporter()
        configure_obs(exporter_instance=spy)

        @traced("phronesis.test.async", attributes_from=lambda *, key: {"key": key})
        async def fn(*, key: str) -> str:
            return key

        await fn(key="abc")

        assert dict(spy.exported[0].attributes)["key"] == "abc"
