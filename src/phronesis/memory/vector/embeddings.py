"""Reproducible embedding provider intended for tests only.

:class:`DeterministicEmbeddingProvider` derives a fixed-length vector
from the SHA-256 digest of each input text. Same text + same instance
always produces the same vector. Different texts produce different
vectors with high probability.

The provider has **no semantic meaning** - similar texts do not
produce similar vectors. Suitable for verifying store wiring,
ordering and persistence without taking a dependency on a real
embedding service.
"""

from __future__ import annotations

import hashlib
import struct
from collections.abc import Sequence


class DeterministicEmbeddingProvider:
    """Hash-based embedder yielding reproducible vectors for tests."""

    def __init__(self, dimensions: int = 16) -> None:
        """Create a provider that emits vectors of length ``dimensions``.

        Args:
            dimensions: Number of float components per vector. Must be
                strictly positive.

        Raises:
            ValueError: if ``dimensions`` is not positive.
        """
        if dimensions <= 0:
            raise ValueError("dimensions must be a positive integer")

        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        """Return the configured vector length."""
        return self._dimensions

    async def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        """Return one deterministic vector per input text."""
        return tuple(self._embed_single(text) for text in texts)

    def _embed_single(self, text: str) -> tuple[float, ...]:
        components: list[float] = []
        counter = 0

        while len(components) < self._dimensions:
            payload = f"{text}|{counter}".encode()
            digest = hashlib.sha256(payload).digest()

            for i in range(0, len(digest), 4):
                if len(components) >= self._dimensions:
                    break

                chunk = digest[i : i + 4]
                value = struct.unpack(">I", chunk)[0]
                components.append((value / 0xFFFFFFFF) * 2.0 - 1.0)

            counter += 1

        return tuple(components)
