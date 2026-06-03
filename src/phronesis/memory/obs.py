"""Observability attributes and span helpers for memory operations.

Follows the same dot-separated naming used by
:mod:`phronesis.obs.attributes`. Constants are :class:`Final` strings so
call sites cannot accidentally mutate them.

``MEMORY_SCOPE_ID`` is high-cardinality: include it as a **span
attribute** but never as a **metric label**, otherwise the metric
backend will explode.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Final

from phronesis.memory.scope import MemoryScope
from phronesis.obs.spans import start_span_async

# Scope ---------------------------------------------------------------

MEMORY_SCOPE_LEVEL: Final[str] = "memory.scope.level"
MEMORY_SCOPE_ID: Final[str] = "memory.scope.id"

# Store ---------------------------------------------------------------

MEMORY_STORE_TYPE: Final[str] = "memory.store.type"
MEMORY_STORE_BACKEND: Final[str] = "memory.store.backend"

# Operation -----------------------------------------------------------

MEMORY_OP: Final[str] = "memory.op"
MEMORY_ITEMS_COUNT: Final[str] = "memory.items.count"

# Vector search -------------------------------------------------------

MEMORY_SEARCH_TOP_K: Final[str] = "memory.search.top_k"
MEMORY_SEARCH_MIN_SCORE: Final[str] = "memory.search.min_score"
MEMORY_SEARCH_RESULTS: Final[str] = "memory.search.results"

# Store types ---------------------------------------------------------

STORE_TYPE_WORKING: Final[str] = "working"
STORE_TYPE_KV: Final[str] = "kv"
STORE_TYPE_VECTOR: Final[str] = "vector"
STORE_TYPE_EPISODIC: Final[str] = "episodic"

# Backends ------------------------------------------------------------

BACKEND_IN_MEMORY: Final[str] = "in_memory"
BACKEND_FILESYSTEM_JSON: Final[str] = "filesystem_json"


def scope_attributes(scope: MemoryScope) -> dict[str, Any]:
    """Return a span-attribute dict describing ``scope``."""
    attrs: dict[str, Any] = {MEMORY_SCOPE_LEVEL: scope.level.value}

    if scope.id is not None:
        attrs[MEMORY_SCOPE_ID] = scope.id

    return attrs


@asynccontextmanager
async def memory_span(
    op: str,
    *,
    store_type: str,
    backend: str,
    scope: MemoryScope,
    extra: dict[str, Any] | None = None,
) -> AsyncIterator[Any]:
    """Open a ``phronesis.memory.<op>`` span with the standard attributes.

    Args:
        op: Operation name (``"get"``, ``"set"``, ``"search"``, ...).
        store_type: One of the ``STORE_TYPE_*`` constants.
        backend: One of the ``BACKEND_*`` constants.
        scope: Scope the operation targets.
        extra: Optional extra attributes merged into the span.

    Yields:
        The active span (real or no-op).
    """
    attrs: dict[str, Any] = {
        MEMORY_OP: op,
        MEMORY_STORE_TYPE: store_type,
        MEMORY_STORE_BACKEND: backend,
    }
    attrs.update(scope_attributes(scope))

    if extra:
        attrs.update(extra)

    async with start_span_async(
        f"phronesis.memory.{op}",
        attributes=attrs,
    ) as span:
        yield span
