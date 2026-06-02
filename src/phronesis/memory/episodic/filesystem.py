"""JSONL append-only filesystem episodic store.

Each scope is persisted to ``<root>/<level>/<id>.jsonl``. Records are
appended one per line; queries parse the file end-to-beginning when
filtering applies. There is no compaction: scopes grow until the
caller explicitly calls :meth:`delete`.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from phronesis.memory.episodic.protocol import Episode
from phronesis.memory.errors import MemoryBackendError
from phronesis.memory.scope import MemoryLevel, MemoryScope


class FilesystemJSONEpisodicStore:
    """Episodic backend persisting one JSONL file per scope, append-only."""

    def __init__(self, root: str | Path) -> None:
        """Create the backend rooted at ``root``."""
        self._root = Path(root)
        self._locks: dict[MemoryScope, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._registry_lock = asyncio.Lock()

    async def _lock_for(self, scope: MemoryScope) -> asyncio.Lock:
        async with self._registry_lock:
            return self._locks[scope]

    def _path_for(self, scope: MemoryScope) -> Path:
        if scope.level is MemoryLevel.GLOBAL:
            return self._root / "global.jsonl"

        assert scope.id is not None

        return self._root / scope.level.value / f"{scope.id}.jsonl"

    def _read_all(self, scope: MemoryScope) -> list[Episode]:
        path = self._path_for(scope)

        if not path.exists():
            return []

        episodes: list[Episode] = []

        try:
            with path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()

                    if not line:
                        continue

                    raw = json.loads(line)
                    episodes.append(_episode_from_raw(raw, scope))
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            raise MemoryBackendError(
                f"failed to read episodic store at {path}",
                details={"path": str(path)},
            ) from exc

        return episodes

    async def record(self, episode: Episode) -> None:
        """Append ``episode`` to its scope's JSONL file."""
        lock = await self._lock_for(episode.scope)
        path = self._path_for(episode.scope)
        record = {
            "episode_id": episode.episode_id,
            "timestamp": episode.timestamp,
            "type": episode.type,
            "payload": dict(episode.payload),
        }

        async with lock:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)

                with path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record))
                    fh.write("\n")
            except OSError as exc:
                raise MemoryBackendError(
                    f"failed to append episode at {path}",
                    details={"path": str(path)},
                ) from exc

    async def query(
        self,
        scope: MemoryScope,
        types: Sequence[str] = (),
        since: float | None = None,
        limit: int = 100,
    ) -> tuple[Episode, ...]:
        """Return episodes from ``scope`` filtered by ``types`` and ``since``."""
        if limit <= 0:
            return ()

        type_set = set(types)
        lock = await self._lock_for(scope)

        async with lock:
            episodes = self._read_all(scope)

        survivors: list[Episode] = []

        for ep in episodes:
            if type_set and ep.type not in type_set:
                continue

            if since is not None and ep.timestamp < since:
                continue

            survivors.append(ep)

        survivors.sort(key=lambda e: e.timestamp)

        return tuple(survivors[:limit])

    async def latest(self, scope: MemoryScope, type: str) -> Episode | None:
        """Return the most recent episode of ``type`` in ``scope``."""
        lock = await self._lock_for(scope)

        async with lock:
            episodes = self._read_all(scope)

        matching = [ep for ep in episodes if ep.type == type]

        if not matching:
            return None

        return max(matching, key=lambda e: e.timestamp)

    async def delete(self, scope: MemoryScope) -> int:
        """Delete every episode persisted for ``scope``."""
        lock = await self._lock_for(scope)
        path = self._path_for(scope)

        async with lock:
            if not path.exists():
                return 0

            try:
                episodes = self._read_all(scope)
                path.unlink()

                return len(episodes)
            except OSError as exc:
                raise MemoryBackendError(
                    f"failed to delete episodic store at {path}",
                    details={"path": str(path)},
                ) from exc


def _episode_from_raw(raw: dict[str, Any], scope: MemoryScope) -> Episode:
    return Episode(
        episode_id=raw["episode_id"],
        scope=scope,
        timestamp=float(raw["timestamp"]),
        type=raw["type"],
        payload=raw.get("payload", {}),
    )
