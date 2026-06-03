"""Hierarchical namespace key for memory operations.

Every store operation is parameterised by a :class:`MemoryScope` so the
same backend can serve data belonging to different agents, sessions,
runs or pipeline runs without leakage. The scope is a small, frozen
value object: ``(level, id)``.

:class:`MemoryLevel` is closed: callers cannot invent new levels. The
``GLOBAL`` level is the only one allowed to omit the id; every other
level requires a non-empty id string.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from phronesis.memory.errors import MemoryScopeError


class MemoryLevel(StrEnum):
    """Closed enumeration of valid scope levels.

    Attributes:
        GLOBAL: Process-wide scope shared across every run.
        AGENT: Tied to a single :class:`phronesis.agents.id.AgentId`.
        SESSION: Tied to a multi-turn
            :class:`phronesis.communication.session_id.SessionId`.
        RUN: Tied to a single :class:`phronesis.agents.run.RunId`.
        PIPELINE_RUN: Tied to a pipeline-level run identifier.
    """

    GLOBAL = "global"
    AGENT = "agent"
    SESSION = "session"
    RUN = "run"
    PIPELINE_RUN = "pipeline_run"


@dataclass(frozen=True, slots=True)
class MemoryScope:
    """Namespace key paired with every memory operation.

    Frozen and hashable so it can be used as a dict key in in-memory
    backends and as a path fragment in filesystem backends.

    Attributes:
        level: One of :class:`MemoryLevel`.
        id: String identifier within the level. Required for every
            level except :attr:`MemoryLevel.GLOBAL`, where it must be
            ``None``.
    """

    level: MemoryLevel
    id: str | None = None

    def __post_init__(self) -> None:
        """Validate the ``(level, id)`` invariant.

        Raises:
            MemoryScopeError: if ``id`` is missing for a non-global
                level, or present for the global level.
        """
        if self.level is MemoryLevel.GLOBAL and self.id is not None:
            raise MemoryScopeError(
                "MemoryLevel.GLOBAL must not carry an id.",
                details={"level": str(self.level), "id": self.id},
            )

        if self.level is not MemoryLevel.GLOBAL and not self.id:
            raise MemoryScopeError(
                f"MemoryLevel.{self.level.name} requires a non-empty id.",
                details={"level": str(self.level)},
            )

    @classmethod
    def global_(cls) -> MemoryScope:
        """Return the process-wide :attr:`MemoryLevel.GLOBAL` scope."""
        return cls(level=MemoryLevel.GLOBAL, id=None)

    @classmethod
    def agent(cls, agent_id: str) -> MemoryScope:
        """Return a scope bound to an agent id."""
        return cls(level=MemoryLevel.AGENT, id=agent_id)

    @classmethod
    def session(cls, session_id: str) -> MemoryScope:
        """Return a scope bound to a session id."""
        return cls(level=MemoryLevel.SESSION, id=session_id)

    @classmethod
    def run(cls, run_id: str) -> MemoryScope:
        """Return a scope bound to a run id."""
        return cls(level=MemoryLevel.RUN, id=run_id)

    @classmethod
    def pipeline_run(cls, pipeline_run_id: str) -> MemoryScope:
        """Return a scope bound to a pipeline-run id."""
        return cls(level=MemoryLevel.PIPELINE_RUN, id=pipeline_run_id)

    @property
    def key(self) -> str:
        """Stable string representation suitable for paths and labels.

        Returns:
            ``"<level>"`` for ``GLOBAL``, ``"<level>:<id>"`` otherwise.
        """
        if self.id is None:
            return self.level.value

        return f"{self.level.value}:{self.id}"
