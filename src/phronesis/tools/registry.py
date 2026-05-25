"""Tool registry and ``tool_scope`` context manager.

A process-wide registry holds declared tools, keyed by canonical id.
:func:`tool_scope` swaps the active registry for the duration of a
``with`` block using a :class:`~contextvars.ContextVar`, so concurrent
async scopes (tests, isolated agent runs) never bleed into each other.
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
    """Thread-safe mapping of canonical tool id to :class:`Tool`."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._lock = threading.RLock()

    def register(self, tool: Tool) -> None:
        """Register ``tool`` under its canonical id.

        Re-registering the **same** :class:`Tool` instance is a no-op
        (idempotent on module re-import). Registering a different tool
        under an already-taken id raises :class:`DuplicateToolError`.
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

        Raises:
            ToolNotFoundError: if no tool is registered under that id.
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
        """Return a snapshot tuple of all registered tools."""
        with self._lock:
            return tuple(self._tools.values())

    def clear(self) -> None:
        """Remove every registered tool."""
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
