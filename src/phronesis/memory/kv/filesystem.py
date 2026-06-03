"""JSON-per-scope filesystem KV backend with atomic writes.

Each scope is persisted to a single JSON file at
``<root>/<level>/<id>.json`` (``<root>/global.json`` for the global
level). Writes are atomic: the backend dumps to a temporary file in
the same directory and renames via :func:`os.replace`, which the OS
guarantees to be atomic on the same filesystem.

TTL is stored alongside the value as an absolute wall-clock
``expires_at`` (seconds since epoch). Expiry is lazy on read.

Concurrency caveat: atomicity is per-write, not transactional across
processes. Two processes writing the same scope concurrently may lose
one of the two updates. Acceptable for single-process workloads;
documented as a known limit.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from phronesis.memory.errors import MemoryBackendError
from phronesis.memory.scope import MemoryLevel, MemoryScope


class FilesystemJSONKeyValueStore:
    """KV backend persisting one JSON file per scope."""

    def __init__(self, root: str | Path) -> None:
        """Create the backend rooted at ``root``.

        Args:
            root: Directory used as the storage root. Created on
                demand the first time a scope is written.
        """
        self._root = Path(root)
        self._locks: dict[MemoryScope, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._registry_lock = asyncio.Lock()

    async def _lock_for(self, scope: MemoryScope) -> asyncio.Lock:
        async with self._registry_lock:
            return self._locks[scope]

    def _path_for(self, scope: MemoryScope) -> Path:
        if scope.level is MemoryLevel.GLOBAL:
            return self._root / "global.json"

        assert scope.id is not None

        return self._root / scope.level.value / f"{scope.id}.json"

    def _load(self, scope: MemoryScope) -> dict[str, dict[str, Any]]:
        path = self._path_for(scope)

        if not path.exists():
            return {}

        try:
            with path.open("r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            raise MemoryBackendError(
                f"failed to read kv store at {path}",
                details={"path": str(path)},
            ) from exc

        if not isinstance(raw, dict):
            raise MemoryBackendError(
                f"kv store at {path} is not a JSON object",
                details={"path": str(path)},
            )

        return raw

    def _dump(self, scope: MemoryScope, data: dict[str, dict[str, Any]]) -> None:
        path = self._path_for(scope)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            fd, tmp_name = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=str(path.parent))

            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(data, fh)

                os.replace(tmp_name, path)
            except Exception:
                Path(tmp_name).unlink(missing_ok=True)
                raise
        except OSError as exc:
            raise MemoryBackendError(
                f"failed to write kv store at {path}",
                details={"path": str(path)},
            ) from exc

    def _alive(self, entry: dict[str, Any]) -> bool:
        expires_at = entry.get("expires_at")

        if expires_at is None:
            return True

        return float(expires_at) > time.time()

    async def get(self, scope: MemoryScope, key: str) -> Any | None:
        """Return the live value at ``key`` or ``None``."""
        lock = await self._lock_for(scope)

        async with lock:
            data = self._load(scope)
            entry = data.get(key)

            if entry is None:
                return None

            if not self._alive(entry):
                data.pop(key, None)
                self._dump(scope, data)

                return None

            return entry["value"]

    async def set(
        self,
        scope: MemoryScope,
        key: str,
        value: Any,
        ttl_s: float | None = None,
    ) -> None:
        """Persist ``value`` under ``key`` with optional ``ttl_s``."""
        lock = await self._lock_for(scope)
        expires_at = time.time() + ttl_s if ttl_s is not None else None

        async with lock:
            data = self._load(scope)
            data[key] = {"value": value, "expires_at": expires_at}
            self._dump(scope, data)

    async def delete(self, scope: MemoryScope, key: str) -> bool:
        """Delete ``key`` and report whether it existed."""
        lock = await self._lock_for(scope)

        async with lock:
            data = self._load(scope)

            if key not in data:
                return False

            del data[key]
            self._dump(scope, data)

            return True

    async def list_keys(self, scope: MemoryScope, prefix: str = "") -> tuple[str, ...]:
        """Return the sorted tuple of live keys under ``prefix``."""
        lock = await self._lock_for(scope)

        async with lock:
            data = self._load(scope)
            survived: dict[str, dict[str, Any]] = {}
            alive_keys: list[str] = []

            for k, entry in data.items():
                if not self._alive(entry):
                    continue

                survived[k] = entry

                if k.startswith(prefix):
                    alive_keys.append(k)

            if len(survived) != len(data):
                self._dump(scope, survived)

            return tuple(sorted(alive_keys))

    async def compare_and_swap(
        self,
        scope: MemoryScope,
        key: str,
        expected: Any,
        new: Any,
    ) -> bool:
        """Atomically swap when the current value equals ``expected``."""
        lock = await self._lock_for(scope)

        async with lock:
            data = self._load(scope)
            entry = data.get(key)
            current = entry["value"] if entry is not None and self._alive(entry) else None

            if current != expected:
                return False

            data[key] = {"value": new, "expires_at": None}
            self._dump(scope, data)

            return True

    async def append(self, scope: MemoryScope, key: str, value: Any) -> None:
        """Append ``value`` to the list at ``key``."""
        lock = await self._lock_for(scope)

        async with lock:
            data = self._load(scope)
            entry = data.get(key)

            if entry is None or not self._alive(entry):
                data[key] = {"value": [value], "expires_at": None}
                self._dump(scope, data)
                return

            if not isinstance(entry["value"], list):
                raise TypeError(
                    f"kv key {key!r} holds {type(entry['value']).__name__}, "
                    "expected list for append()",
                )

            entry["value"].append(value)
            self._dump(scope, data)

    async def increment(self, scope: MemoryScope, key: str, delta: int = 1) -> int:
        """Atomically increment the integer at ``key``."""
        lock = await self._lock_for(scope)

        async with lock:
            data = self._load(scope)
            entry = data.get(key)
            current = entry["value"] if entry is not None and self._alive(entry) else 0

            if not isinstance(current, int):
                raise TypeError(
                    f"kv key {key!r} holds {type(current).__name__}, expected int for increment()",
                )

            new_value = current + delta
            data[key] = {"value": new_value, "expires_at": None}
            self._dump(scope, data)

            return new_value
