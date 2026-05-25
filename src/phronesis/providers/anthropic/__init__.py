"""Anthropic provider implementation.

See ``docs/PROVIDERS-DECISIONS.md``. Public entry point is the
:func:`anthropic` factory; the underlying ``AnthropicProvider`` class is
framework-internal.
"""

from __future__ import annotations

from phronesis.providers.anthropic.factory import anthropic

__all__ = [
    "anthropic",
]
