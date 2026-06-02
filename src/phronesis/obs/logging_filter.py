"""Logging filter that correlates log records with the active span.

Provides :class:`TraceCorrelationFilter` and the global
``install_trace_correlation_filter`` / ``uninstall_trace_correlation_filter``
helpers used by :func:`phronesis.obs.config.configure_obs` to add
``trace_id`` and ``span_id`` to every log record produced while an
OpenTelemetry span is active.

Both fields are written in the canonical hex form used by the
OpenTelemetry specification: 32 hex characters for the trace id and 16
hex characters for the span id, so log entries can be correlated 1:1
with the traces exported by the same process.

Implementation note: the helpers install a wrapper around
``logging.setLogRecordFactory`` so the enrichment covers every logger
in the process, not just loggers below ``phronesis``. When the
``obs`` extra is not installed, the wrapper short-circuits and never
imports OpenTelemetry.
"""

from __future__ import annotations

import logging
from typing import Any

from phronesis.obs._detect import OBS_AVAILABLE

_FACTORY_MARKER_ATTR = "_phronesis_obs_factory"


class TraceCorrelationFilter(logging.Filter):
    """Logging filter that attaches ``trace_id`` and ``span_id`` to records.

    Always returns ``True``: this filter never drops records, it only
    enriches them when a valid OpenTelemetry span is active.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        _enrich_record(record)

        return True


def _enrich_record(record: logging.LogRecord) -> None:
    if not OBS_AVAILABLE:
        return

    from opentelemetry import trace

    span = trace.get_current_span()
    ctx = span.get_span_context()

    if not ctx.is_valid:
        return

    record.trace_id = format(ctx.trace_id, "032x")
    record.span_id = format(ctx.span_id, "016x")


_original_factory: Any = None


def install_trace_correlation_filter() -> None:
    """Wrap the global ``LogRecordFactory`` so every record is enriched.

    Idempotent: subsequent calls return immediately when the wrapper is
    already installed. ``uninstall_trace_correlation_filter`` restores
    the previously active factory.
    """
    global _original_factory

    current = logging.getLogRecordFactory()

    if getattr(current, _FACTORY_MARKER_ATTR, False):
        return

    _original_factory = current

    def _factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = current(*args, **kwargs)
        _enrich_record(record)

        return record

    _factory._phronesis_obs_factory = True  # type: ignore[attr-defined]
    logging.setLogRecordFactory(_factory)


def uninstall_trace_correlation_filter() -> None:
    """Restore the previously installed ``LogRecordFactory``."""
    global _original_factory

    if _original_factory is None:
        return

    logging.setLogRecordFactory(_original_factory)
    _original_factory = None
