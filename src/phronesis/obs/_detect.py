"""Runtime detection of OpenTelemetry availability.

Importing this module never fails: ``OBS_AVAILABLE`` captures whether
the optional ``obs`` extra is installed so the rest of the package can
switch between real OpenTelemetry calls and no-op fallbacks without
try/except scattered around the codebase.

The check is performed exactly once at import time. Installing or
uninstalling OpenTelemetry after the package is imported will not be
reflected until the process restarts.
"""

from __future__ import annotations

from importlib.util import find_spec


def _probe_opentelemetry() -> bool:
    try:
        trace_spec = find_spec("opentelemetry.trace")
        metrics_spec = find_spec("opentelemetry.metrics")
    except ModuleNotFoundError:
        return False

    return trace_spec is not None and metrics_spec is not None


OBS_AVAILABLE: bool = _probe_opentelemetry()
