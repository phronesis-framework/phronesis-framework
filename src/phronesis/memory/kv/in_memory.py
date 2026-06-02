"""Process-local key-value backend with lazy TTL expiry.

The backend is a single :class:`dict` per scope, guarded by one
:class:`asyncio.Lock` per scope. TTL is enforced lazily: expired
entries are evicted only when a caller reads them or lists the keys
of their scope. There is no background sweeper.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from phronesis.memory.scope import MemoryScope


@dataclass(slots=True)
class _Entry:
    value: Any
    expires_at: float | None


class InMemoryKeyValueStore:
    """In-memory KV backend with atomic ops and lazy TTL expiry."""

    def __init__(self) -> None:
        """Create an empty store."""
        self._data: dict[MemoryScope, dict[str, _Entry]] = defaultdict(dict)
        self._locks: dict[MemoryScope, asyncio.Lock] = {}
        self._registry_lock = asyncio.Lock()

    async def _lock_for(self, scope: MemoryScope) -> asyncio.Lock:
        async with self._registry_lock:
            lock = self._locks.get(scope)

            if lock is None:
                lock = asyncio.Lock()
                self._locks[scope] = lock

            return lock

    def _alive(self, entry: _Entry) -> bool:
        if entry.expires_at is None:
            return True

        return entry.expires_at > time.monotonic()

    async def get(self, scope: MemoryScope, key: str) -> Any | None:
        """Return the live value at ``key`` or ``None``."""
        lock = await self._lock_for(scope)

        async with lock:
            bucket = self._data.get(scope)

            if not bucket:
                return None

            entry = bucket.get(key)

            if entry is None:
                return None

            if not self._alive(entry):
                bucket.pop(key, None)

                return None

            return entry.value

    async def set(
        self,
        scope: MemoryScope,
        key: str,
        value: Any,
        ttl_s: float | None = None,
    ) -> None:
        """Store ``value`` under ``key`` with optional ``ttl_s``."""
        lock = await self._lock_for(scope)
        expires_at = time.monotonic() + ttl_s if ttl_s is not None else None

        async with lock:
            self._data[scope][key] = _Entry(value=value, expires_at=expires_at)

    async def delete(self, scope: MemoryScope, key: str) -> bool:
        """Delete ``key`` from ``scope`` and report whether it existed."""
        lock = await self._lock_for(scope)

        async with lock:
            bucket = self._data.get(scope)

            if not bucket or key not in bucket:
                return False

            del bucket[key]

            return True

    async def list_keys(self, scope: MemoryScope, prefix: str = "") -> tuple[str, ...]:
        """Return the sorted tuple of live keys under ``prefix``."""
        lock = await self._lock_for(scope)

        async with lock:
            bucket = self._data.get(scope, {})
            alive_keys: list[str] = []

            for k, entry in list(bucket.items()):
                if not self._alive(entry):
                    bucket.pop(k, None)
                    continue

                if not k.startswith(prefix):
                    continue

                alive_keys.append(k)

            return tuple(sorted(alive_keys))

    async def compare_and_swap(
        self,
        scope: MemoryScope,
        key: str,
        expected: Any,
        new: Any,
    ) -> bool:
        """Atomically swap when the current value equals ``expected``."""
        lock = await self._lock_for(scope)

        async with lock:
            bucket = self._data[scope]
            entry = bucket.get(key)
            current = entry.value if entry is not None and self._alive(entry) else None

            if current != expected:
                return False

            bucket[key] = _Entry(value=new, expires_at=None)

            return True

    async def append(self, scope: MemoryScope, key: str, value: Any) -> None:
        """Append ``value`` to the list at ``key``."""
        lock = await self._lock_for(scope)

        async with lock:
            bucket = self._data[scope]
            entry = bucket.get(key)

            if entry is None or not self._alive(entry):
                bucket[key] = _Entry(value=[value], expires_at=None)
                return

            if not isinstance(entry.value, list):
                raise TypeError(
                    f"kv key {key!r} holds {type(entry.value).__name__}, "
                    "expected list for append()",
                )

            entry.value.append(value)

    async def increment(self, scope: MemoryScope, key: str, delta: int = 1) -> int:
        """Atomically increment the integer at ``key``."""
        lock = await self._lock_for(scope)

        async with lock:
            bucket = self._data[scope]
            entry = bucket.get(key)
            current = entry.value if entry is not None and self._alive(entry) else 0

            if not isinstance(current, int):
                raise TypeError(
                    f"kv key {key!r} holds {type(current).__name__}, expected int for increment()",
                )

            new_value = current + delta
            bucket[key] = _Entry(value=new_value, expires_at=None)

            return new_value
