"""Tool registry and ``tool_scope`` context manager.

A process-wide :class:`_ToolRegistry` holds every declared tool keyed
by canonical id. The :func:`tool` decorator registers into the
*active* registry - by default the global one, but tests and isolated
workloads can swap it with :func:`tool_scope` so declarations do not
leak into the rest of the process.

The active registry is stored in a :class:`contextvars.ContextVar`
so concurrent async scopes (e.g. multiple ``asyncio.Task`` instances)
each see their own value.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from phronesis.tools.errors import DuplicateToolError, ToolNotFoundError
from phronesis.tools.tool import Tool
from phronesis.tools.tool_id import ToolId


class _ToolRegistry:
    """Thread-safe mapping of canonical tool id to :class:`Tool`.

    Internal. Callers reach into the registry through
    :func:`current_registry` and :func:`tool_scope`. All mutations
    are guarded by an :class:`RLock` so the registry can be populated
    from import-time code on multiple threads safely.
    """

    def __init__(self) -> None:
        """Create an empty registry."""
        self._tools: dict[str, Tool] = {}
        self._lock = threading.RLock()

    def register(self, tool: Tool) -> None:
        """Register ``tool`` under its canonical id.

        Re-registering the **same** :class:`Tool` instance is a
        no-op so module re-imports remain idempotent. Registering a
        *different* tool under an already-taken id raises.

        Args:
            tool: The tool to register. The id is read from
                ``tool.spec.id.canonical``.

        Raises:
            DuplicateToolError: if another distinct tool is already
                registered under the same id.
        """
        key = tool.spec.id.canonical

        with self._lock:
            existing = self._tools.get(key)

            if existing is tool:
                return

            if existing is not None:
                raise DuplicateToolError(
                    f"Tool id {key!r} is already registered.",
                    details={
                        "id": key,
                        "existing_name": str(existing.spec.name),
                        "incoming_name": str(tool.spec.name),
                    },
                )

            self._tools[key] = tool

    def lookup(self, tool_id: ToolId | str) -> Tool:
        """Return the tool registered under ``tool_id``.

        Args:
            tool_id: Either a :class:`ToolId` instance or its
                canonical string form.

        Returns:
            The :class:`Tool` previously registered under that id.

        Raises:
            ToolNotFoundError: if no tool is registered under
                ``tool_id``.
        """
        key = tool_id.canonical if isinstance(tool_id, ToolId) else tool_id

        with self._lock:
            tool = self._tools.get(key)

        if tool is None:
            raise ToolNotFoundError(
                f"No tool registered under id {key!r}.",
                details={"id": key},
            )

        return tool

    def all(self) -> tuple[Tool, ...]:
        """Return an immutable snapshot of every registered tool.

        The snapshot is captured under the lock so it cannot change
        while the caller iterates over it.

        Returns:
            Tuple of registered :class:`Tool` instances in insertion
            order.
        """
        with self._lock:
            return tuple(self._tools.values())

    def clear(self) -> None:
        """Remove every registered tool from this registry."""
        with self._lock:
            self._tools.clear()


_global_registry: _ToolRegistry = _ToolRegistry()

_active_registry: ContextVar[_ToolRegistry] = ContextVar(
    "phronesis_tools_active_registry",
    default=_global_registry,
)


def current_registry() -> _ToolRegistry:
    """Return the registry active in the current async context."""
    return _active_registry.get()


@contextmanager
def tool_scope() -> Iterator[_ToolRegistry]:
    """Activate an isolated registry for the duration of the ``with`` block.

    Tools declared inside the block register into the scoped registry, not
    the global one. The previous registry is restored on exit, even if an
    exception propagates.
    """
    scoped = _ToolRegistry()
    token = _active_registry.set(scoped)

    try:
        yield scoped
    finally:
        _active_registry.reset(token)
