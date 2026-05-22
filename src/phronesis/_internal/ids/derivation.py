"""Helpers to derive canonical identifiers from Python objects."""

from __future__ import annotations

from collections.abc import Callable


def canonical_from_function(fn: Callable[..., object]) -> str:
    """Derive a canonical id from a function's module and qualified name."""
    return f"{fn.__module__}.{fn.__qualname__}".lower()
