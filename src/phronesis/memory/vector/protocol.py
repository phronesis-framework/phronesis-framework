"""Structural contracts for vector memory and embedding providers.

The two protocols are deliberately decoupled so callers can mix and
match: the same :class:`InMemoryVectorStore` can be paired with a
remote OpenAI embedder or with the
:class:`DeterministicEmbeddingProvider` used in tests.

Similarity is left to backends; the framework convention is cosine
similarity in ``[-1.0, 1.0]`` with higher values meaning more similar.
The ``min_score`` argument filters candidates strictly below the
threshold.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Final, Protocol, runtime_checkable

from phronesis.memory.scope import MemoryScope

_EMPTY_METADATA: Final[Mapping[str, Any]] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class VectorItem:
    """A single stored vector together with its source text and metadata.

    Attributes:
        id: Stable identifier within the owning scope. Upserting a new
            item with an existing id overwrites the previous entry.
        text: Source text that produced ``embedding``. Returned to the
            caller verbatim on search so the model receives the
            original snippet.
        embedding: The vector representation as a tuple of floats.
        metadata: Free-form mapping coerced to a read-only
            :class:`MappingProxyType` in ``__post_init__``.
    """

    id: str
    text: str
    embedding: tuple[float, ...]
    metadata: Mapping[str, Any] = field(default_factory=lambda: _EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Stateless contract for producing embeddings from text."""

    async def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        """Return one embedding per input text, in the same order."""
        ...

    @property
    def dimensions(self) -> int:
        """Return the size of every embedding produced by this provider."""
        ...


@runtime_checkable
class VectorStore(Protocol):
    """Structural contract for vector backends."""

    async def upsert(self, scope: MemoryScope, items: Sequence[VectorItem]) -> None:
        """Insert or overwrite ``items`` in ``scope`` keyed by ``item.id``."""
        ...

    async def search(
        self,
        scope: MemoryScope,
        query_embedding: Sequence[float],
        k: int = 5,
        min_score: float = 0.0,
    ) -> tuple[tuple[VectorItem, float], ...]:
        """Return the top ``k`` items in ``scope`` ranked by cosine similarity.

        The result is a tuple of ``(item, score)`` pairs sorted by
        descending score. Pairs with ``score < min_score`` are
        filtered out before truncating to ``k``.
        """
        ...

    async def delete(self, scope: MemoryScope, ids: Sequence[str]) -> int:
        """Delete every id in ``ids`` from ``scope``. Return the number removed."""
        ...

    async def count(self, scope: MemoryScope) -> int:
        """Return the number of items currently stored in ``scope``."""
        ...
