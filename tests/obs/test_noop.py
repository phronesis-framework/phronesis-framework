"""Tests for the no-op span fallback used when OpenTelemetry is absent."""

from __future__ import annotations

import pytest

from phronesis.obs._noop import _NoopSpan


class TestNoopMethods:
    def test_set_attribute_returns_none(self) -> None:
        span = _NoopSpan()

        assert span.set_attribute("key", "value") is None

    def test_set_attributes_returns_none(self) -> None:
        span = _NoopSpan()

        assert span.set_attributes({"a": 1, "b": "x"}) is None

    def test_record_exception_returns_none(self) -> None:
        span = _NoopSpan()

        assert span.record_exception(RuntimeError("boom")) is None

    def test_record_exception_with_attributes_returns_none(self) -> None:
        span = _NoopSpan()

        assert span.record_exception(RuntimeError("boom"), {"k": "v"}) is None

    def test_set_status_returns_none(self) -> None:
        span = _NoopSpan()

        assert span.set_status("OK") is None

    def test_set_status_with_description_returns_none(self) -> None:
        span = _NoopSpan()

        assert span.set_status("ERROR", "details") is None

    def test_add_event_returns_none(self) -> None:
        span = _NoopSpan()

        assert span.add_event("checkpoint") is None

    def test_add_event_with_attributes_returns_none(self) -> None:
        span = _NoopSpan()

        assert span.add_event("checkpoint", {"phase": "init"}) is None

    def test_end_returns_none(self) -> None:
        span = _NoopSpan()

        assert span.end() is None


class TestSyncContextManager:
    def test_enter_yields_self(self) -> None:
        span = _NoopSpan()

        with span as entered:
            assert entered is span

    def test_exit_returns_none(self) -> None:
        span = _NoopSpan()

        result = span.__exit__(None, None, None)

        assert result is None

    def test_exception_propagates(self) -> None:
        span = _NoopSpan()

        with pytest.raises(ValueError), span:
            raise ValueError("bubble up")


class TestAsyncContextManager:
    async def test_aenter_yields_self(self) -> None:
        span = _NoopSpan()

        async with span as entered:
            assert entered is span

    async def test_aexit_returns_none(self) -> None:
        span = _NoopSpan()

        result = await span.__aexit__(None, None, None)

        assert result is None

    async def test_exception_propagates(self) -> None:
        span = _NoopSpan()

        with pytest.raises(ValueError):
            async with span:
                raise ValueError("bubble up")


class TestReusability:
    def test_same_instance_can_be_reentered(self) -> None:
        span = _NoopSpan()

        with span:
            pass

        with span:
            pass
