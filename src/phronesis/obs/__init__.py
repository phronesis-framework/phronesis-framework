"""Observability infrastructure for the Phronesis framework.

This package provides the public API for traces, spans, metrics and
log correlation built on top of OpenTelemetry.

OpenTelemetry is an optional dependency exposed through the ``obs`` extra.
When the extra is not installed, every entry point in this package
behaves as a no-op so that import and call sites stay safe regardless
of the runtime environment.

Subpackage layout:

- ``_detect``        — runtime detection of OpenTelemetry availability.
- ``_noop``          — no-op fallbacks used when OpenTelemetry is absent.
- ``attributes``     — closed catalog of standard span attribute names.
- ``config``         — ``configure_obs`` and the global configuration state.
- ``spans``          — ``traced`` decorator and ``start_span`` context manager.
- ``metrics``        — closed catalog of standard metric instruments.
- ``logging_filter`` — ``logging.Filter`` that correlates logs with the
  active span via ``trace_id`` and ``span_id``.
"""

from __future__ import annotations

from phronesis.obs import attributes as attributes
from phronesis.obs import metrics as metrics
from phronesis.obs.config import ObsConfig as ObsConfig
from phronesis.obs.config import configure_obs as configure_obs
from phronesis.obs.errors import ObsConfigError as ObsConfigError
from phronesis.obs.errors import ObsError as ObsError
from phronesis.obs.errors import ObsNotAvailableError as ObsNotAvailableError
from phronesis.obs.spans import current_trace_id as current_trace_id
from phronesis.obs.spans import start_span as start_span
from phronesis.obs.spans import start_span_async as start_span_async
from phronesis.obs.spans import traced as traced

__all__ = [
    "ObsConfig",
    "ObsConfigError",
    "ObsError",
    "ObsNotAvailableError",
    "attributes",
    "configure_obs",
    "current_trace_id",
    "metrics",
    "start_span",
    "start_span_async",
    "traced",
]
