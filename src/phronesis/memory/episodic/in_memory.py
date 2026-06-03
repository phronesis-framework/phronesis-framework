"""Process-local episodic store backed by an append-only list per scope."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Sequence

from phronesis.memory.episodic.protocol import Episode
from phronesis.memory.scope import MemoryScope


class InMemoryEpisodicStore:
    """Episodic backend keeping episodes in a list per scope."""

    def __init__(self) -> None:
        """Create an empty store."""
        self._data: dict[MemoryScope, list[Episode]] = defaultdict(list)
        self._locks: dict[MemoryScope, asyncio.Lock] = {}
        self._registry_lock = asyncio.Lock()

    async def _lock_for(self, scope: MemoryScope) -> asyncio.Lock:
        async with self._registry_lock:
            lock = self._locks.get(scope)

            if lock is None:
                lock = asyncio.Lock()
                self._locks[scope] = lock

            return lock

    async def record(self, episode: Episode) -> None:
        """Append ``episode`` to its scope."""
        lock = await self._lock_for(episode.scope)

        async with lock:
            self._data[episode.scope].append(episode)

    async def query(
        self,
        scope: MemoryScope,
        types: Sequence[str] = (),
        since: float | None = None,
        limit: int = 100,
    ) -> tuple[Episode, ...]:
        """Return episodes from ``scope`` filtered by ``types`` and ``since``."""
        if limit <= 0:
            return ()

        type_set = set(types)
        lock = await self._lock_for(scope)

        async with lock:
            bucket = list(self._data.get(scope, ()))

        survivors: list[Episode] = []

        for ep in bucket:
            if type_set and ep.type not in type_set:
                continue

            if since is not None and ep.timestamp < since:
                continue

            survivors.append(ep)

        survivors.sort(key=lambda e: e.timestamp)

        return tuple(survivors[:limit])

    async def latest(self, scope: MemoryScope, type: str) -> Episode | None:
        """Return the most recent episode of ``type`` in ``scope`` or ``None``."""
        lock = await self._lock_for(scope)

        async with lock:
            bucket = list(self._data.get(scope, ()))

        matching = [ep for ep in bucket if ep.type == type]

        if not matching:
            return None

        return max(matching, key=lambda e: e.timestamp)

    async def delete(self, scope: MemoryScope) -> int:
        """Delete every episode in ``scope``."""
        lock = await self._lock_for(scope)

        async with lock:
            existing = self._data.pop(scope, [])

            return len(existing)
