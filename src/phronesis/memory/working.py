"""Per-scope working memory: short-lived state for a run or session.

Working memory is the agent's scratchpad. It holds values produced
during the current run (intermediate notes, partial plans, branch
state for TreeSearch, etc.) and is expected to disappear when the
run ends - unless a :class:`phronesis.memory.checkpoint.Checkpointer`
snapshots it.

:class:`WorkingMemoryStore` is the structural contract; backends
implement it. The framework ships
:class:`InMemoryWorkingStore` as the default backend.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from phronesis.memory.scope import MemoryScope


@runtime_checkable
class WorkingMemoryStore(Protocol):
    """Structural contract for working-memory backends.

    Every method is scoped: callers pass an explicit :class:`MemoryScope`
    so a single backend instance can serve many concurrent runs without
    cross-contamination.
    """

    async def set(self, scope: MemoryScope, key: str, value: Any) -> None:
        """Store ``value`` under ``key`` in ``scope``, overwriting any prior value."""
        ...

    async def get(self, scope: MemoryScope, key: str) -> Any | None:
        """Return the value stored at ``key`` in ``scope``, or ``None`` if absent."""
        ...

    async def append(self, scope: MemoryScope, key: str, value: Any) -> None:
        """Append ``value`` to the list stored at ``key``, creating it if missing."""
        ...

    async def list_keys(self, scope: MemoryScope) -> tuple[str, ...]:
        """Return all keys currently set in ``scope`` as a stable tuple."""
        ...

    async def clear(self, scope: MemoryScope) -> None:
        """Remove every key stored in ``scope``."""
        ...

    async def snapshot(self, scope: MemoryScope) -> dict[str, Any]:
        """Return a deep-ish copy of every key/value in ``scope``."""
        ...

    async def restore(self, scope: MemoryScope, snapshot: Mapping[str, Any]) -> None:
        """Replace the contents of ``scope`` with ``snapshot``."""
        ...


class InMemoryWorkingStore:
    """Process-local working memory backed by a ``dict`` per scope.

    Atomicity is enforced with one :class:`asyncio.Lock` per scope so
    blackboard-style patterns (Supervisor, Debate) stay race-free
    inside a single event loop.
    """

    def __init__(self) -> None:
        """Create an empty store."""
        self._data: dict[MemoryScope, dict[str, Any]] = defaultdict(dict)
        self._locks: dict[MemoryScope, asyncio.Lock] = {}
        self._registry_lock = asyncio.Lock()

    async def _lock_for(self, scope: MemoryScope) -> asyncio.Lock:
        async with self._registry_lock:
            lock = self._locks.get(scope)

            if lock is None:
                lock = asyncio.Lock()
                self._locks[scope] = lock

            return lock

    async def set(self, scope: MemoryScope, key: str, value: Any) -> None:
        """Store ``value`` under ``key`` in ``scope``."""
        lock = await self._lock_for(scope)

        async with lock:
            self._data[scope][key] = value

    async def get(self, scope: MemoryScope, key: str) -> Any | None:
        """Return the value at ``key`` in ``scope`` or ``None``."""
        lock = await self._lock_for(scope)

        async with lock:
            return self._data.get(scope, {}).get(key)

    async def append(self, scope: MemoryScope, key: str, value: Any) -> None:
        """Append ``value`` to the list at ``key`` in ``scope``.

        Creates the list lazily. Raises ``TypeError`` if ``key``
        already holds a non-list value.
        """
        lock = await self._lock_for(scope)

        async with lock:
            bucket = self._data[scope]
            existing = bucket.get(key)

            if existing is None:
                bucket[key] = [value]
                return

            if not isinstance(existing, list):
                raise TypeError(
                    f"working memory key {key!r} holds {type(existing).__name__}, "
                    "expected list for append()",
                )

            existing.append(value)

    async def list_keys(self, scope: MemoryScope) -> tuple[str, ...]:
        """Return the sorted tuple of keys currently set in ``scope``."""
        lock = await self._lock_for(scope)

        async with lock:
            return tuple(sorted(self._data.get(scope, {}).keys()))

    async def clear(self, scope: MemoryScope) -> None:
        """Remove every key from ``scope``."""
        lock = await self._lock_for(scope)

        async with lock:
            self._data.pop(scope, None)

    async def snapshot(self, scope: MemoryScope) -> dict[str, Any]:
        """Return a shallow copy of every key/value in ``scope``.

        Lists are copied positionally so callers cannot mutate the
        live state via the returned snapshot. Mappings nested inside
        values are **not** deep-copied.
        """
        lock = await self._lock_for(scope)

        async with lock:
            source = self._data.get(scope, {})
            out: dict[str, Any] = {}

            for k, v in source.items():
                if isinstance(v, list):
                    out[k] = list(v)
                    continue

                out[k] = v

            return out

    async def restore(self, scope: MemoryScope, snapshot: Mapping[str, Any]) -> None:
        """Replace the contents of ``scope`` with ``snapshot``."""
        lock = await self._lock_for(scope)

        async with lock:
            self._data[scope] = dict(snapshot)
