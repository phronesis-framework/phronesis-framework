"""Runtime detection of OpenTelemetry availability.

Importing this module never fails: the ``OBS_AVAILABLE`` flag captures
whether the optional ``obs`` extra is installed so the rest of the
package can switch between real OpenTelemetry calls and no-op fallbacks
without try/except scattered around the codebase.
"""

from __future__ import annotations
