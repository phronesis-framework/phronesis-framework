"""Agent registry and ``agent_scope`` context manager.

See ``docs/AGENTS-DECISIONS.md`` (D-09): a process-wide registry holds
declared agents; ``agent_scope()`` swaps the active registry via a
:class:`ContextVar` so concurrent async scopes do not bleed into each
other. Mirrors :mod:`phronesis.tools.registry`.
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
    """No agent is registered under the requested id."""


class _AgentRegistry:
    """Thread-safe mapping of canonical agent id to :class:`Agent`."""

    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}
        self._lock = threading.RLock()

    def register(self, agent: Agent) -> None:
        """Register ``agent`` under its canonical id.

        Re-registering the **same** :class:`Agent` instance is a no-op
        (idempotent on module re-import). Registering a different agent
        under an already-taken id raises :class:`DuplicateAgentError`.
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

        Raises:
            AgentNotFoundError: if no agent is registered under that id.
        """
        key = agent_id.canonical if isinstance(agent_id, AgentId) else agent_id

        with self._lock:
            agent = self._agents.get(key)

        if agent is None:
            raise AgentNotFoundError(f"No agent registered under id {key!r}.")

        return agent

    def all(self) -> tuple[Agent, ...]:
        """Return a snapshot tuple of all registered agents."""
        with self._lock:
            return tuple(self._agents.values())

    def clear(self) -> None:
        """Remove every registered agent."""
        with self._lock:
            self._agents.clear()


_global_registry: _AgentRegistry = _AgentRegistry()

_active_registry: ContextVar[_AgentRegistry] = ContextVar(
    "phronesis_agents_active_registry",
    default=_global_registry,
)


def current_registry() -> _AgentRegistry:
    """Return the registry active in the current async context."""
    return _active_registry.get()


@contextmanager
def agent_scope() -> Iterator[_AgentRegistry]:
    """Activate an isolated registry for the duration of the ``with`` block.

    Agents declared inside the block register into the scoped registry,
    not the global one. The previous registry is restored on exit, even
    if an exception propagates.
    """
    scoped = _AgentRegistry()
    token = _active_registry.set(scoped)

    try:
        yield scoped
    finally:
        _active_registry.reset(token)
