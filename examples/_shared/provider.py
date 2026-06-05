"""Provider selection for the examples catalog.

The catalog has three modes of operation, picked from environment
variables in this order:

1. ``CASSETTE_PATH`` set -> :class:`ReplayProvider` reading that file.
   Used by the smoke tests in ``tests/examples/`` so they never touch
   the network.
2. ``RECORD_CASSETTE`` set -> :class:`RecordingProvider` that wraps a
   real Ollama provider and writes responses to disk. Used when the
   maintainer wants to refresh a cassette against a local model.
3. Neither set -> a plain :func:`ollama` provider pointing at the
   local Ollama server.

The defaults match the cassettes committed under each example.
"""

from __future__ import annotations

import os

from phronesis.providers import ollama
from phronesis.providers.protocol import LLMProvider
from phronesis.replay import RecordingProvider, ReplayProvider

DEFAULT_MODEL = "qwen3.5:9b"
DEFAULT_HOST = "http://localhost:11434"


def build_provider(default_model: str = DEFAULT_MODEL) -> LLMProvider:
    """Return the provider configured for the current environment.

    Args:
        default_model: Ollama model tag used when ``OLLAMA_MODEL`` is
            not set. Each example picks the model it was recorded with.

    Returns:
        A :class:`LLMProvider` ready to be passed to ``@agent(model=...)``.
    """
    cassette = os.environ.get("CASSETTE_PATH")

    if cassette:
        return ReplayProvider(cassette)

    model = os.environ.get("OLLAMA_MODEL", default_model)
    host = os.environ.get("OLLAMA_HOST", DEFAULT_HOST)

    real: LLMProvider = ollama(model=model, host=host)

    record = os.environ.get("RECORD_CASSETTE")

    if record:
        return RecordingProvider(inner=real, cassette_path=record)

    return real
