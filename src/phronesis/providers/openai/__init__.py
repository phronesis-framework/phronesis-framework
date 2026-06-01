"""OpenAI provider implementation.

The public entry point is the :func:`openai` factory; the underlying
``OpenAIProvider`` class is framework-internal. :func:`ollama`,
:func:`vllm` and :func:`openwebui` are thin wrappers that pre-fill
``base_url``, auth and a conservative capability set for each
OpenAI-compatible runtime.
"""

from __future__ import annotations

from phronesis.providers.openai.factory import openai
from phronesis.providers.openai.helpers import ollama, openwebui, vllm

__all__ = [
    "ollama",
    "openai",
    "openwebui",
    "vllm",
]
