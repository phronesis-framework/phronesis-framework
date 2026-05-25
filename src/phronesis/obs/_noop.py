"""No-op fallbacks used when OpenTelemetry is not installed.

These types satisfy the surface of the public obs API so call sites do
not need to branch on whether the ``obs`` extra is available.
"""

from __future__ import annotations
