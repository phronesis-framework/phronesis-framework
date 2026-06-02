"""Per-tool result cache.

A :class:`CachePolicy` describes whether and how the agent loop
should memoise the result of a :class:`Tool` invocation. Policies are
attached to the :class:`Tool` wrapper at decoration time and consulted
by :meth:`Tool.invoke` before the underlying callable runs.

Caching is opt-in and intentionally local to a single :class:`Tool`
instance: registries do not share state, and the cache disappears
with the tool. Only successful invocations are stored — exceptions
are propagated unchanged so retry semantics remain unaffected.

The default policy is :data:`NO_CACHE`, which short-circuits the
cache logic entirely so non-cached tools pay no overhead.
"""

from __future__ import annotations

import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CachePolicy:
    """Configuration for a tool's result cache.

    Attributes:
        max_size: Maximum number of distinct argument tuples kept in
            the cache. ``0`` disables caching entirely. When the
            cache is full an LRU entry is evicted on insert.
        ttl_seconds: Optional time-to-live, in seconds, applied to
            each stored entry. ``None`` means entries never expire on
            their own (LRU is the only eviction signal).
    """

    max_size: int = 128
    ttl_seconds: float | None = None

    def __post_init__(self) -> None:
        if self.max_size < 0:
            object.__setattr__(self, "max_size", 0)

        if self.ttl_seconds is not None and self.ttl_seconds < 0:
            object.__setattr__(self, "ttl_seconds", 0.0)

    @property
    def enabled(self) -> bool:
        """Return ``True`` when the policy stores entries at all."""
        return self.max_size > 0


NO_CACHE: CachePolicy = CachePolicy(max_size=0)
"""Singleton policy meaning "do not cache"."""


def make_cache_key(args: dict[str, Any]) -> str:
    """Build a stable, hashable cache key from a tool's arguments.

    Arguments are serialised as JSON with sorted keys so two
    equivalent dicts produce the same key regardless of insertion
    order. Non-JSON-serialisable values fall back to their
    :func:`repr`, which is stable for primitive containers and
    dataclasses with deterministic ``__repr__``.

    Args:
        args: The validated argument dict passed to the tool's
            callable. The runtime :class:`Context`, when present,
            must already be excluded by the caller — it is not part
            of the cache identity.

    Returns:
        A deterministic string suitable as a cache key.
    """
    try:
        return json.dumps(args, sort_keys=True, default=repr)
    except TypeError:
        return repr(sorted(args.items()))


class ToolCache:
    """LRU + TTL store for a single :class:`Tool`.

    Instances are created lazily by :class:`Tool` when the attached
    :class:`CachePolicy` is enabled. The class is intentionally
    minimal: no concurrency primitives, no metrics, no persistence.
    The agent loop is single-threaded per run, so an
    :class:`OrderedDict` is enough.
    """

    __slots__ = ("_policy", "_store")

    def __init__(self, policy: CachePolicy) -> None:
        self._policy = policy
        self._store: OrderedDict[str, tuple[Any, float | None]] = OrderedDict()

    def get(self, key: str) -> tuple[bool, Any]:
        """Look up ``key``.

        Returns:
            ``(True, value)`` on a hit, ``(False, None)`` on a miss
            (including expired entries, which are evicted as a side
            effect).
        """
        if key not in self._store:
            return False, None

        value, expires_at = self._store[key]

        if expires_at is not None and time.monotonic() >= expires_at:
            del self._store[key]
            return False, None

        self._store.move_to_end(key)

        return True, value

    def set(self, key: str, value: Any) -> None:
        """Store ``value`` under ``key``, evicting LRU entries if needed."""
        if not self._policy.enabled:
            return

        if self._policy.ttl_seconds is not None:
            expires_at: float | None = time.monotonic() + self._policy.ttl_seconds
        else:
            expires_at = None

        self._store[key] = (value, expires_at)
        self._store.move_to_end(key)

        while len(self._store) > self._policy.max_size:
            self._store.popitem(last=False)

    def clear(self) -> None:
        """Drop every entry. Useful for tests and explicit invalidation."""
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)
