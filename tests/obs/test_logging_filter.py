"""Tests for the trace correlation logging filter."""

from __future__ import annotations

import logging

import pytest

from phronesis.obs import logging_filter as logging_filter_module
from phronesis.obs._detect import OBS_AVAILABLE
from phronesis.obs.config import configure_obs
from phronesis.obs.logging_filter import (
    TraceCorrelationFilter,
    install_trace_correlation_filter,
    uninstall_trace_correlation_filter,
)
from phronesis.obs.spans import start_span


def _make_record() -> logging.LogRecord:
    return logging.LogRecord(
        name="phronesis.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=None,
        exc_info=None,
    )


class TestTraceCorrelationFilterWithoutSpan:
    def test_filter_returns_true(self) -> None:
        record = _make_record()
        flt = TraceCorrelationFilter()

        assert flt.filter(record) is True

    @pytest.mark.skipif(not OBS_AVAILABLE, reason="obs extra not installed")
    def test_filter_does_not_add_fields_without_active_span(self) -> None:
        configure_obs()
        record = _make_record()
        flt = TraceCorrelationFilter()

        flt.filter(record)

        assert not hasattr(record, "trace_id")
        assert not hasattr(record, "span_id")


@pytest.mark.skipif(not OBS_AVAILABLE, reason="obs extra not installed")
class TestTraceCorrelationFilterWithSpan:
    def test_filter_adds_trace_id_and_span_id(self) -> None:
        configure_obs()
        flt = TraceCorrelationFilter()

        with start_span("phronesis.test.span"):
            record = _make_record()
            flt.filter(record)

        assert hasattr(record, "trace_id")
        assert hasattr(record, "span_id")

    def test_trace_id_is_32_hex_chars(self) -> None:
        configure_obs()
        flt = TraceCorrelationFilter()

        with start_span("phronesis.test.span"):
            record = _make_record()
            flt.filter(record)

        trace_id: str = record.trace_id  # type: ignore[attr-defined]

        assert len(trace_id) == 32
        int(trace_id, 16)

    def test_span_id_is_16_hex_chars(self) -> None:
        configure_obs()
        flt = TraceCorrelationFilter()

        with start_span("phronesis.test.span"):
            record = _make_record()
            flt.filter(record)

        span_id: str = record.span_id  # type: ignore[attr-defined]

        assert len(span_id) == 16
        int(span_id, 16)


class TestInstallTraceCorrelationFilter:
    def test_install_wraps_factory(self) -> None:
        original = logging.getLogRecordFactory()

        install_trace_correlation_filter()

        assert logging.getLogRecordFactory() is not original

    def test_install_is_idempotent(self) -> None:
        install_trace_correlation_filter()
        first_factory = logging.getLogRecordFactory()

        install_trace_correlation_filter()

        assert logging.getLogRecordFactory() is first_factory

    @pytest.mark.skipif(not OBS_AVAILABLE, reason="obs extra not installed")
    def test_factory_enriches_records_globally(self) -> None:
        configure_obs()
        install_trace_correlation_filter()

        with start_span("phronesis.test.span"):
            logger = logging.getLogger("some.unrelated.logger")
            record = logger.makeRecord(
                "some.unrelated.logger",
                logging.INFO,
                __file__,
                1,
                "msg",
                (),
                None,
            )

        assert hasattr(record, "trace_id")
        assert hasattr(record, "span_id")

    @pytest.mark.skipif(not OBS_AVAILABLE, reason="obs extra not installed")
    def test_factory_does_not_enrich_without_active_span(self) -> None:
        configure_obs()
        install_trace_correlation_filter()

        logger = logging.getLogger("some.other.logger")
        record = logger.makeRecord(
            "some.other.logger",
            logging.INFO,
            __file__,
            1,
            "msg",
            (),
            None,
        )

        assert not hasattr(record, "trace_id")


class TestUninstallTraceCorrelationFilter:
    def test_uninstall_restores_previous_factory(self) -> None:
        original = logging.getLogRecordFactory()
        install_trace_correlation_filter()

        uninstall_trace_correlation_filter()

        assert logging.getLogRecordFactory() is original

    def test_uninstall_without_install_is_noop(self) -> None:
        original = logging.getLogRecordFactory()

        uninstall_trace_correlation_filter()

        assert logging.getLogRecordFactory() is original

    def test_uninstall_is_idempotent(self) -> None:
        install_trace_correlation_filter()
        uninstall_trace_correlation_filter()
        original = logging.getLogRecordFactory()

        uninstall_trace_correlation_filter()

        assert logging.getLogRecordFactory() is original


class TestObsAvailableShortCircuit:
    def test_enrich_returns_early_when_obs_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(logging_filter_module, "OBS_AVAILABLE", False)
        record = _make_record()
        flt = TraceCorrelationFilter()

        flt.filter(record)

        assert not hasattr(record, "trace_id")
        assert not hasattr(record, "span_id")
