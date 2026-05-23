"""Derive canonical ids from Python objects."""

from __future__ import annotations

from collections.abc import Callable


def canonical_from_function(fn: Callable[..., object]) -> str:
    """Lowercase ``module.qualname`` of ``fn``."""
    return f"{fn.__module__}.{fn.__qualname__}".lower()
