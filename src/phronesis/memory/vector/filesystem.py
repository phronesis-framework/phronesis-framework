"""JSONL-per-scope filesystem vector backend.

Each scope is persisted to ``<root>/<level>/<id>.jsonl`` as a list of
JSON objects, one per :class:`VectorItem`. Writes rewrite the file
atomically through a temporary file rename.

Search performs a full scan of the file and is O(n) per query.
Acceptable for fewer than a few thousand items per scope; documented
as a hard upper bound. Larger workloads should plug in a dedicated
vector database behind the same :class:`VectorStore` Protocol.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from collections import defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path

from phronesis.memory.errors import MemoryBackendError
from phronesis.memory.scope import MemoryLevel, MemoryScope
from phronesis.memory.vector._cosine import cosine_similarity
from phronesis.memory.vector.protocol import VectorItem


class FilesystemJSONVectorStore:
    """Vector backend persisting one JSONL file per scope."""

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

    def _load(self, scope: MemoryScope) -> dict[str, VectorItem]:
        path = self._path_for(scope)

        if not path.exists():
            return {}

        items: dict[str, VectorItem] = {}

        try:
            with path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()

                    if not line:
                        continue

                    raw = json.loads(line)
                    item = VectorItem(
                        id=raw["id"],
                        text=raw["text"],
                        embedding=tuple(raw["embedding"]),
                        metadata=raw.get("metadata", {}),
                    )
                    items[item.id] = item
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            raise MemoryBackendError(
                f"failed to read vector store at {path}",
                details={"path": str(path)},
            ) from exc

        return items

    def _dump(self, scope: MemoryScope, items: Iterable[VectorItem]) -> None:
        path = self._path_for(scope)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            fd, tmp_name = tempfile.mkstemp(prefix=".tmp-", suffix=".jsonl", dir=str(path.parent))

            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    for item in items:
                        record = {
                            "id": item.id,
                            "text": item.text,
                            "embedding": list(item.embedding),
                            "metadata": dict(item.metadata),
                        }
                        fh.write(json.dumps(record))
                        fh.write("\n")

                os.replace(tmp_name, path)
            except Exception:
                Path(tmp_name).unlink(missing_ok=True)
                raise
        except OSError as exc:
            raise MemoryBackendError(
                f"failed to write vector store at {path}",
                details={"path": str(path)},
            ) from exc

    async def upsert(self, scope: MemoryScope, items: Sequence[VectorItem]) -> None:
        """Insert or overwrite ``items`` keyed by ``item.id``."""
        lock = await self._lock_for(scope)

        async with lock:
            current = self._load(scope)

            for item in items:
                current[item.id] = item

            self._dump(scope, current.values())

    async def search(
        self,
        scope: MemoryScope,
        query_embedding: Sequence[float],
        k: int = 5,
        min_score: float = 0.0,
    ) -> tuple[tuple[VectorItem, float], ...]:
        """Return the top ``k`` items by cosine similarity."""
        if k <= 0:
            return ()

        lock = await self._lock_for(scope)

        async with lock:
            current = self._load(scope)
            scored: list[tuple[VectorItem, float]] = []

            for item in current.values():
                score = cosine_similarity(query_embedding, item.embedding)

                if score < min_score:
                    continue

                scored.append((item, score))

            scored.sort(key=lambda pair: pair[1], reverse=True)

            return tuple(scored[:k])

    async def delete(self, scope: MemoryScope, ids: Sequence[str]) -> int:
        """Delete the listed ``ids`` and return how many were removed."""
        lock = await self._lock_for(scope)

        async with lock:
            current = self._load(scope)
            removed = 0

            for ident in ids:
                if current.pop(ident, None) is not None:
                    removed += 1

            if removed:
                self._dump(scope, current.values())

            return removed

    async def count(self, scope: MemoryScope) -> int:
        """Return the number of items stored in ``scope``."""
        lock = await self._lock_for(scope)

        async with lock:
            return len(self._load(scope))
