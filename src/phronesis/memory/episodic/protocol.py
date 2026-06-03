"""Episode dataclass and the structural :class:`EpisodicStore` contract.

Episodic memory is an append-only event log. Episodes are emitted by
the framework (run lifecycle, checkpoints, supervisor decisions) and
by user code (custom audit events). The store is queryable by type
and time but never mutated in place: the immutability is part of the
contract so checkpoint restoration and reproduction are well-defined.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Final, Protocol, runtime_checkable

from phronesis.memory.scope import MemoryScope

_EMPTY_PAYLOAD: Final[Mapping[str, Any]] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class Episode:
    """A single recorded event within a scope.

    Attributes:
        episode_id: Stable identifier within the owning scope.
        scope: Scope the episode was recorded in.
        timestamp: Wall-clock seconds since the epoch when the episode
            was recorded.
        type: Free-form category. Convention is dot-separated lower
            case (``"run_started"``, ``"tool_call"``, ``"checkpoint"``).
        payload: Free-form mapping coerced to read-only.
    """

    episode_id: str
    scope: MemoryScope
    timestamp: float
    type: str
    payload: Mapping[str, Any] = field(default_factory=lambda: _EMPTY_PAYLOAD)

    def __post_init__(self) -> None:
        if not isinstance(self.payload, MappingProxyType):
            object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))


@runtime_checkable
class EpisodicStore(Protocol):
    """Append-only, scope-aware event log."""

    async def record(self, episode: Episode) -> None:
        """Append ``episode`` to its scope."""
        ...

    async def query(
        self,
        scope: MemoryScope,
        types: Sequence[str] = (),
        since: float | None = None,
        limit: int = 100,
    ) -> tuple[Episode, ...]:
        """Return matching episodes from ``scope`` ordered by ascending timestamp.

        Args:
            scope: Scope to query.
            types: Restrict to episodes whose ``type`` is in this
                sequence. Empty means no filter.
            since: Drop episodes with ``timestamp < since``. ``None``
                means no lower bound.
            limit: Maximum number of episodes to return. ``limit <= 0``
                returns an empty tuple.
        """
        ...

    async def latest(self, scope: MemoryScope, type: str) -> Episode | None:
        """Return the most recent episode of ``type`` in ``scope`` or ``None``."""
        ...

    async def delete(self, scope: MemoryScope) -> int:
        """Delete every episode in ``scope``. Return how many were removed."""
        ...
