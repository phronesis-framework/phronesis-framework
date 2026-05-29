"""Executable agent wrapper.

See ``docs/AGENTS-DECISIONS.md`` (D-02, D-09): :class:`Agent` is the
callable side of an agent declaration; ``agent.spec`` is the pure-data
side. ``run()`` and ``stream()`` are implemented in later phases (loop,
streaming, session) and intentionally raise here so the registry can
hold a working :class:`Agent` from day one.
"""

from __future__ import annotations

from phronesis.agents.id import AgentId
from phronesis.agents.spec import AgentSpec


class Agent:
    """Callable wrapper exposing an :class:`AgentSpec`.

    The spec is treated as the source of truth; the wrapper holds no
    additional configuration of its own. Identity is the spec's id.
    """

    __slots__ = ("spec",)

    def __init__(self, spec: AgentSpec) -> None:
        self.spec = spec

    @property
    def id(self) -> AgentId:
        """Stable identifier of the underlying :class:`AgentSpec`."""
        return self.spec.id

    @property
    def name(self) -> str:
        """LLM-facing name of the agent."""
        return self.spec.name

    def __repr__(self) -> str:
        return f"Agent(id={self.spec.id.canonical!r}, name={self.spec.name!r})"
