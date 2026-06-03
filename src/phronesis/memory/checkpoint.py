"""Pause/resume API built on working + episodic memory.

A :class:`Checkpoint` is a snapshot of working memory plus a free-form
``cursor`` describing how the run should resume (current iteration,
branch identifier, plan step, etc.). Checkpoints are recorded as
episodes of type ``"checkpoint"``; restoration emits a follow-up
``"checkpoint_restored"`` episode so the audit trail is complete.

This is **snapshot-based**, not event-sourced: ``restore`` overwrites
the current working memory of the scope with the snapshot. The
framework does not replay deltas.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Final

from phronesis.memory.episodic.protocol import Episode, EpisodicStore
from phronesis.memory.errors import CheckpointNotFoundError
from phronesis.memory.scope import MemoryScope
from phronesis.memory.working import WorkingMemoryStore

_EMPTY_MAPPING: Final[Mapping[str, Any]] = MappingProxyType({})

CHECKPOINT_TYPE: Final[str] = "checkpoint"
"""Episode type emitted by :meth:`Checkpointer.save`."""

CHECKPOINT_RESTORED_TYPE: Final[str] = "checkpoint_restored"
"""Episode type emitted by :meth:`Checkpointer.restore`."""


@dataclass(frozen=True, slots=True)
class Checkpoint:
    """Snapshot of working memory plus a cursor for resuming a run.

    Attributes:
        checkpoint_id: Stable identifier unique within the scope.
        scope: Scope this checkpoint belongs to.
        working_snapshot: Frozen view of the working memory at save
            time.
        cursor: Free-form mapping describing how the run should
            resume (iteration index, branch id, plan step, etc.).
        timestamp: Wall-clock seconds since the epoch at save time.
    """

    checkpoint_id: str
    scope: MemoryScope
    working_snapshot: Mapping[str, Any]
    cursor: Mapping[str, Any] = field(default_factory=lambda: _EMPTY_MAPPING)
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.working_snapshot, MappingProxyType):
            object.__setattr__(
                self,
                "working_snapshot",
                MappingProxyType(dict(self.working_snapshot)),
            )

        if not isinstance(self.cursor, MappingProxyType):
            object.__setattr__(self, "cursor", MappingProxyType(dict(self.cursor)))


class Checkpointer:
    """Save and restore working-memory snapshots via the episodic store."""

    def __init__(
        self,
        working: WorkingMemoryStore,
        episodic: EpisodicStore,
    ) -> None:
        """Bind the two stores this checkpointer uses.

        Args:
            working: Backend providing working-memory snapshots.
            episodic: Backend persisting the checkpoint episodes.
        """
        self._working = working
        self._episodic = episodic

    async def save(
        self,
        scope: MemoryScope,
        cursor: Mapping[str, Any] | None = None,
    ) -> Checkpoint:
        """Snapshot working memory and emit a ``checkpoint`` episode.

        Args:
            scope: Scope to checkpoint.
            cursor: Optional resume context. Defaults to empty mapping.

        Returns:
            The newly created :class:`Checkpoint`.
        """
        snapshot = await self._working.snapshot(scope)
        timestamp = time.time()
        checkpoint_id = f"chk_{uuid.uuid4().hex[:12]}"
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            scope=scope,
            working_snapshot=snapshot,
            cursor=dict(cursor) if cursor is not None else {},
            timestamp=timestamp,
        )

        await self._episodic.record(
            Episode(
                episode_id=checkpoint_id,
                scope=scope,
                timestamp=timestamp,
                type=CHECKPOINT_TYPE,
                payload={
                    "checkpoint_id": checkpoint_id,
                    "working_snapshot": dict(snapshot),
                    "cursor": dict(checkpoint.cursor),
                },
            )
        )

        return checkpoint

    async def load(
        self,
        scope: MemoryScope,
        checkpoint_id: str | None = None,
    ) -> Checkpoint | None:
        """Return a checkpoint by id, or the latest one when ``checkpoint_id`` is None.

        Returns ``None`` when no checkpoint exists; raises
        :class:`CheckpointNotFoundError` when an explicit
        ``checkpoint_id`` is given but no matching episode exists.
        """
        if checkpoint_id is None:
            latest = await self._episodic.latest(scope, CHECKPOINT_TYPE)

            if latest is None:
                return None

            return _checkpoint_from_episode(latest)

        episodes = await self._episodic.query(
            scope,
            types=(CHECKPOINT_TYPE,),
            limit=10_000,
        )

        for ep in episodes:
            if ep.payload.get("checkpoint_id") == checkpoint_id:
                return _checkpoint_from_episode(ep)

        raise CheckpointNotFoundError(
            f"checkpoint {checkpoint_id!r} not found in scope {scope.key}",
            details={"checkpoint_id": checkpoint_id, "scope": scope.key},
        )

    async def restore(
        self,
        scope: MemoryScope,
        checkpoint_id: str | None = None,
    ) -> Checkpoint | None:
        """Restore working memory from a checkpoint and emit an audit episode.

        Returns ``None`` when no checkpoint exists (and
        ``checkpoint_id`` was not specified). When a specific
        ``checkpoint_id`` is given and missing, raises
        :class:`CheckpointNotFoundError`.
        """
        checkpoint = await self.load(scope, checkpoint_id)

        if checkpoint is None:
            return None

        await self._working.restore(scope, checkpoint.working_snapshot)
        await self._episodic.record(
            Episode(
                episode_id=f"rst_{uuid.uuid4().hex[:12]}",
                scope=scope,
                timestamp=time.time(),
                type=CHECKPOINT_RESTORED_TYPE,
                payload={"checkpoint_id": checkpoint.checkpoint_id},
            )
        )

        return checkpoint


def _checkpoint_from_episode(episode: Episode) -> Checkpoint:
    payload = episode.payload

    return Checkpoint(
        checkpoint_id=str(payload.get("checkpoint_id", episode.episode_id)),
        scope=episode.scope,
        working_snapshot=dict(payload.get("working_snapshot", {})),
        cursor=dict(payload.get("cursor", {})),
        timestamp=episode.timestamp,
    )
