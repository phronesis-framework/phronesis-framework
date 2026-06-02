"""Agent registry and ``agent_scope`` context manager.

A process-wide :class:`_AgentRegistry` holds every declared agent
keyed by its canonical id. The :func:`agent` decorator registers each
agent into the registry that is *active in the current context* - by
default this is the global registry, but :func:`agent_scope` lets
tests and isolated workloads swap it out without leaking declarations
into the rest of the process.

The active registry is stored in a :class:`contextvars.ContextVar`,
so concurrent async scopes (e.g. multiple ``asyncio.Task`` instances)
each see their own value.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from phronesis.agents.agent import Agent
from phronesis.agents.errors import DuplicateAgentError
from phronesis.agents.id import AgentId


class AgentNotFoundError(LookupError):
    """Raised by :meth:`_AgentRegistry.lookup` when the id is unknown.

    Subclass of :class:`LookupError` so callers that already handle
    missing-key errors generically continue to work.
    """


class _AgentRegistry:
    """Thread-safe mapping of canonical agent id to :class:`Agent`.

    The registry is internal; callers should reach into it only via
    :func:`current_registry` and :func:`agent_scope`. All mutating
    operations are guarded by an :class:`RLock` so the registry can be
    populated from import-time code on multiple threads safely.
    """

    def __init__(self) -> None:
        """Create an empty registry."""
        self._agents: dict[str, Agent] = {}
        self._lock = threading.RLock()

    def register(self, agent: Agent) -> None:
        """Register ``agent`` under its canonical id.

        Re-registering the **same** :class:`Agent` instance is a
        no-op; this keeps module re-imports idempotent. Registering a
        *different* agent under an already-taken id raises.

        Args:
            agent: The agent to register. Its canonical id is read
                from ``agent.spec.id.canonical``.

        Raises:
            DuplicateAgentError: if another distinct agent is already
                registered under the same id.
        """
        key = agent.spec.id.canonical

        with self._lock:
            existing = self._agents.get(key)

            if existing is agent:
                return

            if existing is not None:
                raise DuplicateAgentError(
                    f"Agent id {key!r} is already registered.",
                    details={
                        "id": key,
                        "existing_name": existing.spec.name,
                        "incoming_name": agent.spec.name,
                    },
                )

            self._agents[key] = agent

    def lookup(self, agent_id: AgentId | str) -> Agent:
        """Return the agent registered under ``agent_id``.

        Args:
            agent_id: Either an :class:`AgentId` instance or its
                canonical string form.

        Returns:
            The :class:`Agent` previously registered under that id.

        Raises:
            AgentNotFoundError: if no agent is registered under
                ``agent_id``.
        """
        key = agent_id.canonical if isinstance(agent_id, AgentId) else agent_id

        with self._lock:
            agent = self._agents.get(key)

        if agent is None:
            raise AgentNotFoundError(f"No agent registered under id {key!r}.")

        return agent

    def all(self) -> tuple[Agent, ...]:
        """Return an immutable snapshot of every registered agent.

        The returned tuple is captured under the lock so it cannot
        change while the caller iterates over it.

        Returns:
            Tuple of registered :class:`Agent` instances in insertion
            order.
        """
        with self._lock:
            return tuple(self._agents.values())

    def clear(self) -> None:
        """Remove every registered agent from this registry."""
        with self._lock:
            self._agents.clear()


_global_registry: _AgentRegistry = _AgentRegistry()

_active_registry: ContextVar[_AgentRegistry] = ContextVar(
    "phronesis_agents_active_registry",
    default=_global_registry,
)


def current_registry() -> _AgentRegistry:
    """Return the registry active in the current async/thread context.

    Outside of an :func:`agent_scope` block this returns the
    process-wide global registry.

    Returns:
        The active :class:`_AgentRegistry`.
    """
    return _active_registry.get()


@contextmanager
def agent_scope() -> Iterator[_AgentRegistry]:
    """Activate an isolated registry for the duration of the ``with`` block.

    Inside the block, every :func:`agent` declaration registers into a
    fresh, scoped registry. The previous registry is restored on exit,
    even when an exception propagates, so the scope cannot leak.

    Yields:
        The scoped :class:`_AgentRegistry` that is active inside the
        block.
    """
    scoped = _AgentRegistry()
    token = _active_registry.set(scoped)

    try:
        yield scoped
    finally:
        _active_registry.reset(token)
