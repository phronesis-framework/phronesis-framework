"""Logging filter that correlates log records with the active span.

Installs a ``logging.Filter`` that, when an OpenTelemetry span is active,
injects ``trace_id`` and ``span_id`` into every log record so the
standard logging pipeline emits records that can be linked to traces.
"""

from __future__ import annotations
