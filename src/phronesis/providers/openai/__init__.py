"""OpenAI provider implementation.

See ``docs/PROVIDERS-DECISIONS.md``. Public entry point is the
:func:`openai` factory; the underlying ``OpenAIProvider`` class is
framework-internal.
"""

from __future__ import annotations

from phronesis.providers.openai.factory import openai

__all__ = [
    "openai",
]
