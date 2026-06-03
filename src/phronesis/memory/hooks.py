"""Agent hook that persists run state into memory on completion.

:class:`MemoryPersistenceHook` is shaped to match
:data:`phronesis.agents.hooks.RunCompleteHook`: an async callable
accepting a :class:`phronesis.agents.run.Result`. Attach it through
:class:`phronesis.agents.hooks.AgentHooks` like any other hook.

On each call the hook snapshots the working memory of the run's
scope into the KV store under ``"last_working_snapshot"`` and
records a ``"run_completed"`` episode when an episodic store is
configured.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING

from phronesis.memory.episodic.protocol import Episode, EpisodicStore
from phronesis.memory.kv.protocol import KeyValueStore
from phronesis.memory.scope import MemoryScope
from phronesis.memory.working import WorkingMemoryStore

if TYPE_CHECKING:
    from phronesis.agents.run import Result


ScopeFromResult = Callable[["Result"], MemoryScope]
"""Callable that derives a :class:`MemoryScope` from a :class:`Result`."""


def _default_scope_fn(result: Result) -> MemoryScope:
    """Default scope derivation: a :attr:`MemoryLevel.RUN` scope from ``run_id``."""
    return MemoryScope.run(result.run_id.canonical)


class MemoryPersistenceHook:
    """Persist working memory and record a run-completed episode."""

    def __init__(
        self,
        working: WorkingMemoryStore,
        kv: KeyValueStore,
        episodic: EpisodicStore | None = None,
        *,
        scope_fn: ScopeFromResult | None = None,
        snapshot_key: str = "last_working_snapshot",
    ) -> None:
        """Wire the stores and the scope-derivation callable.

        Args:
            working: Working store snapshotted at run completion.
            kv: KV store the snapshot is persisted into.
            episodic: Optional episodic store to record a
                ``"run_completed"`` episode.
            scope_fn: Callable mapping a :class:`Result` to a
                :class:`MemoryScope`. Defaults to ``MemoryScope.run(result.run_id.canonical)``.
            snapshot_key: KV key under which the snapshot is stored.
        """
        self._working = working
        self._kv = kv
        self._episodic = episodic
        self._scope_fn = scope_fn if scope_fn is not None else _default_scope_fn
        self._snapshot_key = snapshot_key

    async def __call__(self, result: Result) -> None:
        """Snapshot working memory and emit a run-completed episode."""
        scope = self._scope_fn(result)
        snapshot = await self._working.snapshot(scope)
        await self._kv.set(scope, self._snapshot_key, snapshot)

        if self._episodic is None:
            return

        await self._episodic.record(
            Episode(
                episode_id=f"run_{uuid.uuid4().hex[:12]}",
                scope=scope,
                timestamp=time.time(),
                type="run_completed",
                payload={
                    "run_id": result.run_id.canonical,
                    "iterations": result.iterations,
                    "success": result.success,
                },
            )
        )
