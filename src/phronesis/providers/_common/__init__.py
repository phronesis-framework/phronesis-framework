"""Internal utilities shared across concrete providers.

Reuse happens by composition, not inheritance: helpers live here and
providers consume them as plain functions or small dataclasses.
"""

from __future__ import annotations

__all__: list[str] = []
