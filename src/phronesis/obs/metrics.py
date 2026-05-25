"""Closed catalog of standard metric instruments.

Holds the registry of OpenTelemetry counters and histograms automatically
created when ``configure_obs`` runs, along with no-op fallbacks used
when the ``obs`` extra is not installed.
"""

from __future__ import annotations
