"""Structural contract for key-value memory backends.

The KV store is the building block of the blackboard pattern used by
Supervisor, MapReduce and Debate runtime modes. On top of the usual
get/set/delete/list it exposes three atomic operations -
:meth:`compare_and_swap`, :meth:`append` and :meth:`increment` -
required for race-free concurrent coordination.

TTL is supported on a per-call basis. Backends decide between lazy
(expire on read) and active expiry; both are valid implementations
of this Protocol.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from phronesis.memory.scope import MemoryScope


@runtime_checkable
class KeyValueStore(Protocol):
    """Scoped, atomic-op-capable key-value contract."""

    async def get(self, scope: MemoryScope, key: str) -> Any | None:
        """Return the value at ``key`` in ``scope`` or ``None`` if absent or expired."""
        ...

    async def set(
        self,
        scope: MemoryScope,
        key: str,
        value: Any,
        ttl_s: float | None = None,
    ) -> None:
        """Store ``value`` under ``key``. ``ttl_s`` is the relative TTL in seconds."""
        ...

    async def delete(self, scope: MemoryScope, key: str) -> bool:
        """Remove ``key`` from ``scope``. Return ``True`` if the key existed."""
        ...

    async def list_keys(self, scope: MemoryScope, prefix: str = "") -> tuple[str, ...]:
        """Return the sorted tuple of keys under ``prefix`` in ``scope``."""
        ...

    async def compare_and_swap(
        self,
        scope: MemoryScope,
        key: str,
        expected: Any,
        new: Any,
    ) -> bool:
        """Set ``key`` to ``new`` only if the current value equals ``expected``.

        Returns ``True`` on successful swap, ``False`` otherwise. The
        comparison uses ``==``.
        """
        ...

    async def append(self, scope: MemoryScope, key: str, value: Any) -> None:
        """Append ``value`` to the list at ``key``, creating it on first call."""
        ...

    async def increment(self, scope: MemoryScope, key: str, delta: int = 1) -> int:
        """Atomically add ``delta`` to the integer at ``key`` and return the new value.

        Creates the key with value ``delta`` if it does not exist.
        """
        ...
