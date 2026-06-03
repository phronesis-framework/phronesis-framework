"""In-memory vector store with pure-Python cosine search.

Search is linear in the number of items per scope: every item is
scored, filtered by ``min_score`` and truncated to ``k``. Suitable
for unit tests and small RAG workloads. For larger workloads use a
dedicated vector database (Chroma, Qdrant, etc.) behind the same
:class:`VectorStore` Protocol.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Sequence

from phronesis.memory.scope import MemoryScope
from phronesis.memory.vector._cosine import cosine_similarity
from phronesis.memory.vector.protocol import VectorItem


class InMemoryVectorStore:
    """Process-local vector backend with O(n) cosine search per scope."""

    def __init__(self) -> None:
        """Create an empty store."""
        self._data: dict[MemoryScope, dict[str, VectorItem]] = defaultdict(dict)
        self._locks: dict[MemoryScope, asyncio.Lock] = {}
        self._registry_lock = asyncio.Lock()

    async def _lock_for(self, scope: MemoryScope) -> asyncio.Lock:
        async with self._registry_lock:
            lock = self._locks.get(scope)

            if lock is None:
                lock = asyncio.Lock()
                self._locks[scope] = lock

            return lock

    async def upsert(self, scope: MemoryScope, items: Sequence[VectorItem]) -> None:
        """Insert or overwrite ``items`` keyed by ``item.id``."""
        lock = await self._lock_for(scope)

        async with lock:
            bucket = self._data[scope]

            for item in items:
                bucket[item.id] = item

    async def search(
        self,
        scope: MemoryScope,
        query_embedding: Sequence[float],
        k: int = 5,
        min_score: float = 0.0,
    ) -> tuple[tuple[VectorItem, float], ...]:
        """Return the top ``k`` items by cosine similarity."""
        if k <= 0:
            return ()

        lock = await self._lock_for(scope)

        async with lock:
            bucket = self._data.get(scope, {})
            scored: list[tuple[VectorItem, float]] = []

            for item in bucket.values():
                score = cosine_similarity(query_embedding, item.embedding)

                if score < min_score:
                    continue

                scored.append((item, score))

            scored.sort(key=lambda pair: pair[1], reverse=True)

            return tuple(scored[:k])

    async def delete(self, scope: MemoryScope, ids: Sequence[str]) -> int:
        """Delete the listed ``ids`` and return how many were removed."""
        lock = await self._lock_for(scope)

        async with lock:
            bucket = self._data.get(scope)

            if not bucket:
                return 0

            removed = 0

            for ident in ids:
                if bucket.pop(ident, None) is not None:
                    removed += 1

            return removed

    async def count(self, scope: MemoryScope) -> int:
        """Return the number of items stored in ``scope``."""
        lock = await self._lock_for(scope)

        async with lock:
            return len(self._data.get(scope, {}))
