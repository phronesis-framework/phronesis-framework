"""Tests for :class:`phronesis.memory.FilesystemJSONKeyValueStore`."""

from __future__ import annotations

from pathlib import Path

import pytest

from phronesis.memory.errors import MemoryBackendError
from phronesis.memory.kv import FilesystemJSONKeyValueStore, KeyValueStore
from phronesis.memory.scope import MemoryScope


class TestProtocol:
    def test_implements_protocol(self, tmp_path: Path) -> None:
        assert isinstance(FilesystemJSONKeyValueStore(tmp_path), KeyValueStore)


class TestPersistence:
    @pytest.mark.asyncio
    async def test_value_persists_across_instances(
        self, tmp_path: Path, session_scope: MemoryScope
    ) -> None:
        first = FilesystemJSONKeyValueStore(tmp_path)
        await first.set(session_scope, "k", "v")

        second = FilesystemJSONKeyValueStore(tmp_path)

        assert await second.get(session_scope, "k") == "v"

    @pytest.mark.asyncio
    async def test_atomic_write_does_not_leave_tmp_files(
        self, tmp_path: Path, session_scope: MemoryScope
    ) -> None:
        kv = FilesystemJSONKeyValueStore(tmp_path)

        await kv.set(session_scope, "k", "v")

        stray = [p for p in (tmp_path / "session").iterdir() if p.name.startswith(".tmp-")]

        assert stray == []

    @pytest.mark.asyncio
    async def test_global_scope_uses_dedicated_file(self, tmp_path: Path) -> None:
        kv = FilesystemJSONKeyValueStore(tmp_path)

        await kv.set(MemoryScope.global_(), "k", "v")

        assert (tmp_path / "global.json").exists()


class TestOps:
    @pytest.mark.asyncio
    async def test_cas_works(self, tmp_path: Path, session_scope: MemoryScope) -> None:
        kv = FilesystemJSONKeyValueStore(tmp_path)

        await kv.set(session_scope, "k", "free")

        assert await kv.compare_and_swap(session_scope, "k", "free", "held") is True
        assert await kv.compare_and_swap(session_scope, "k", "free", "x") is False

    @pytest.mark.asyncio
    async def test_increment_persists(self, tmp_path: Path, session_scope: MemoryScope) -> None:
        kv = FilesystemJSONKeyValueStore(tmp_path)

        assert await kv.increment(session_scope, "c") == 1
        kv2 = FilesystemJSONKeyValueStore(tmp_path)

        assert await kv2.increment(session_scope, "c") == 2

    @pytest.mark.asyncio
    async def test_delete_returns_correct_flag(
        self, tmp_path: Path, session_scope: MemoryScope
    ) -> None:
        kv = FilesystemJSONKeyValueStore(tmp_path)

        await kv.set(session_scope, "k", "v")

        assert await kv.delete(session_scope, "k") is True
        assert await kv.delete(session_scope, "k") is False

    @pytest.mark.asyncio
    async def test_list_keys_prefix(self, tmp_path: Path, session_scope: MemoryScope) -> None:
        kv = FilesystemJSONKeyValueStore(tmp_path)

        await kv.set(session_scope, "user.a", 1)
        await kv.set(session_scope, "user.b", 2)
        await kv.set(session_scope, "other", 3)

        assert await kv.list_keys(session_scope, prefix="user.") == (
            "user.a",
            "user.b",
        )

    @pytest.mark.asyncio
    async def test_append_persists_list(self, tmp_path: Path, session_scope: MemoryScope) -> None:
        kv = FilesystemJSONKeyValueStore(tmp_path)

        await kv.append(session_scope, "log", "a")
        await kv.append(session_scope, "log", "b")

        kv2 = FilesystemJSONKeyValueStore(tmp_path)

        assert await kv2.get(session_scope, "log") == ["a", "b"]


class TestCorruption:
    @pytest.mark.asyncio
    async def test_invalid_json_raises_backend_error(
        self, tmp_path: Path, session_scope: MemoryScope
    ) -> None:
        kv = FilesystemJSONKeyValueStore(tmp_path)

        path = tmp_path / "session" / "SID_test.json"
        path.parent.mkdir(parents=True)
        path.write_text("not json", encoding="utf-8")

        with pytest.raises(MemoryBackendError):
            await kv.get(session_scope, "k")
