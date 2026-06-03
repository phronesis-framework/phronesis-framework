"""Tests for :class:`phronesis.memory.FilesystemJSONEpisodicStore`."""

from __future__ import annotations

from pathlib import Path

import pytest

from phronesis.memory.episodic import (
    Episode,
    EpisodicStore,
    FilesystemJSONEpisodicStore,
)
from phronesis.memory.errors import MemoryBackendError
from phronesis.memory.scope import MemoryScope


def _ep(
    scope: MemoryScope,
    *,
    eid: str = "E_x",
    ts: float = 0.0,
    type: str = "run_started",
    payload: dict[str, object] | None = None,
) -> Episode:
    return Episode(
        episode_id=eid,
        scope=scope,
        timestamp=ts,
        type=type,
        payload=payload or {},
    )


class TestProtocol:
    def test_implements_protocol(self, tmp_path: Path) -> None:
        assert isinstance(FilesystemJSONEpisodicStore(tmp_path), EpisodicStore)


class TestPersistence:
    @pytest.mark.asyncio
    async def test_episodes_persist_across_instances(
        self, tmp_path: Path, session_scope: MemoryScope
    ) -> None:
        first = FilesystemJSONEpisodicStore(tmp_path)
        await first.record(_ep(session_scope, eid="a", ts=1.0))
        await first.record(_ep(session_scope, eid="b", ts=2.0))

        second = FilesystemJSONEpisodicStore(tmp_path)

        results = await second.query(session_scope)

        assert tuple(ep.episode_id for ep in results) == ("a", "b")

    @pytest.mark.asyncio
    async def test_global_scope_uses_dedicated_file(self, tmp_path: Path) -> None:
        store = FilesystemJSONEpisodicStore(tmp_path)

        await store.record(_ep(MemoryScope.global_(), eid="g"))

        assert (tmp_path / "global.jsonl").exists()


class TestQueryFilters:
    @pytest.mark.asyncio
    async def test_query_filters_by_type(self, tmp_path: Path, session_scope: MemoryScope) -> None:
        store = FilesystemJSONEpisodicStore(tmp_path)

        await store.record(_ep(session_scope, eid="a", ts=1.0, type="x"))
        await store.record(_ep(session_scope, eid="b", ts=2.0, type="y"))

        results = await store.query(session_scope, types=("y",))

        assert tuple(ep.episode_id for ep in results) == ("b",)

    @pytest.mark.asyncio
    async def test_query_filters_by_since(self, tmp_path: Path, session_scope: MemoryScope) -> None:
        store = FilesystemJSONEpisodicStore(tmp_path)

        await store.record(_ep(session_scope, eid="a", ts=1.0))
        await store.record(_ep(session_scope, eid="b", ts=5.0))

        results = await store.query(session_scope, since=2.0)

        assert tuple(ep.episode_id for ep in results) == ("b",)

    @pytest.mark.asyncio
    async def test_latest_returns_most_recent(
        self, tmp_path: Path, session_scope: MemoryScope
    ) -> None:
        store = FilesystemJSONEpisodicStore(tmp_path)

        await store.record(_ep(session_scope, eid="old", ts=1.0, type="x"))
        await store.record(_ep(session_scope, eid="new", ts=2.0, type="x"))

        latest = await store.latest(session_scope, "x")

        assert latest is not None
        assert latest.episode_id == "new"


class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_removes_file_and_returns_count(
        self, tmp_path: Path, session_scope: MemoryScope
    ) -> None:
        store = FilesystemJSONEpisodicStore(tmp_path)

        await store.record(_ep(session_scope, eid="a"))
        await store.record(_ep(session_scope, eid="b"))

        assert await store.delete(session_scope) == 2
        assert await store.query(session_scope) == ()

    @pytest.mark.asyncio
    async def test_delete_missing_returns_zero(
        self, tmp_path: Path, session_scope: MemoryScope
    ) -> None:
        store = FilesystemJSONEpisodicStore(tmp_path)

        assert await store.delete(session_scope) == 0


class TestCorruption:
    @pytest.mark.asyncio
    async def test_invalid_json_raises_backend_error(
        self, tmp_path: Path, session_scope: MemoryScope
    ) -> None:
        store = FilesystemJSONEpisodicStore(tmp_path)

        path = tmp_path / "session" / "SID_test.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text("not json\n", encoding="utf-8")

        with pytest.raises(MemoryBackendError):
            await store.query(session_scope)
